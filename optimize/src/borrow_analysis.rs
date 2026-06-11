use std::collections::{HashMap, HashSet};

use rustlightast::*;

/// Result of the borrow-analysis pass.
#[derive(Debug, Clone, Default)]
pub struct BorrowAnalysis {
    /// Names of functions whose parameters were rewritten to shared borrows.
    pub borrow_fns: HashSet<String>,
}

// ── Type-level helpers (mirrored from copy_analysis) ─────────────────────────

type TypeEnv = HashMap<String, Type>;

/// Type of a variable after in-place borrow rewriting.
///
/// After B-Match rewrites a match on `v: &D<T>`, every pattern-bound variable
/// `y_j` gets type `&F_j` (where `F_j` is the j-th field type).  For fields
/// that had a `box y_j` pattern (stripped during rewriting) the stored type is
/// still `&Box<F_inner>` – i.e., a reference to the original field type.
type BorrowEnv = HashMap<String, Type>;

#[derive(Debug, Clone)]
struct FieldInfo {
    #[allow(dead_code)]
    name: String,
    ty: Type,
}

#[derive(Debug, Clone)]
struct VariantInfo {
    name: String,
    fields: Vec<Type>,
}

#[derive(Debug, Clone)]
enum TypeDefKind {
    Struct(Vec<FieldInfo>),
    Enum(Vec<VariantInfo>),
}

#[derive(Debug, Clone)]
struct TypeDef {
    generics: Vec<String>,
    kind: TypeDefKind,
}

// ── Demand lattice ────────────────────────────────────────────────────────────

/// Ownership demand on a parameter or derived value (paper §4).
///
/// Demands are ordered by how restrictive they are with respect to shared
/// borrowing.  `Obs`, `Bor`, and `Own` are compatible with converting a
/// parameter to `&T` only when every owned demand passes `OwnOK`.  `Esc` and
/// `Unk` are always blocking.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum Demand {
    /// Purely observational (match scrutinee, boolean predicate).
    Obs,
    /// Consumed through a borrowed interface (`&x`, `.as_ref()`).
    Bor,
    /// Local owned demand satisfiable by cloning/copying without moving
    /// the original (e.g., `x.clone()` used as a constructor field).
    Own(OwnUse),
    /// Borrow escape – blocks borrow inference.
    Esc,
    /// Unknown or unsupported ownership form.
    Unk,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum OwnUse {
    /// Owned value is already produced by an explicit `.clone()` in the source.
    ExplicitClone,
    /// Owned value is obtained by copying a value whose type is known Copy.
    CopyUse,
    /// Ownership-consuming use that is not backed by clone/copy evidence.
    DirectOwned,
}

fn is_blocking(d: Demand) -> bool {
    matches!(d, Demand::Esc | Demand::Unk)
}

fn own_use_ok(source: OwnUse) -> bool {
    matches!(source, OwnUse::ExplicitClone | OwnUse::CopyUse)
}

fn own_ok(demands: &HashSet<Demand>) -> bool {
    demands.iter().all(|demand| match demand {
        Demand::Own(source) => own_use_ok(*source),
        _ => true,
    })
}

// ── Main context ──────────────────────────────────────────────────────────────

struct BorrowContext {
    /// Types known to implement `Copy` (result of the preceding copy pass).
    copy_types: HashSet<String>,
    type_defs: HashMap<String, TypeDef>,
    variant_owners: HashMap<String, Option<String>>,
    /// `fn_name → (generics, param_types, return_type)`
    fn_sigs: HashMap<String, (Vec<GenericParam>, Vec<Type>, Type)>,
    /// `fn_name → sorted list of 0-indexed parameter positions that are
    /// borrowable`.  Populated during phase 1.
    borrow_positions: HashMap<String, Vec<usize>>,
    /// Names of functions whose signatures were rewritten in place.
    borrow_fns: HashSet<String>,
}

/// Infer borrowed parameter interfaces for functions in `module`.
///
/// `copy_types` must be the set produced by `optimize_copy` so that the pass
/// can treat Copy fields as non-consuming uses.
pub fn optimize_borrow(
    module: &mut RustModule,
    copy_types: &HashSet<String>,
) -> BorrowAnalysis {
    let mut analysis = BorrowAnalysis::default();
    optimize_module(module, copy_types, &mut analysis);
    analysis
}

fn optimize_module(
    module: &mut RustModule,
    copy_types: &HashSet<String>,
    analysis: &mut BorrowAnalysis,
) {
    let mut ctx = BorrowContext::from_items(&module.items, copy_types);

    // Three-pass design:
    //  1. Analyse every post-copy function, including _copy specialisations.
    //  2. Rewrite selected parameter types in place.
    //  3. Rewrite bodies and direct calls against the final Borrow(g) summaries.
    ctx.analyse_all_functions(&module.items);
    ctx.rewrite_all_signatures_in_place(&mut module.items);
    ctx.rewrite_all_bodies_and_calls_in_place(&mut module.items);

    analysis.borrow_fns.extend(ctx.borrow_fns.iter().cloned());

    for item in &mut module.items {
        if let Item::Mod(m) = item {
            optimize_module(m, copy_types, analysis);
        }
    }
}

// ── BorrowContext construction ────────────────────────────────────────────────

impl BorrowContext {
    fn from_items(items: &[Item], copy_types: &HashSet<String>) -> Self {
        let mut ctx = Self {
            copy_types: copy_types.clone(),
            type_defs: HashMap::new(),
            variant_owners: HashMap::new(),
            fn_sigs: HashMap::new(),
            borrow_positions: HashMap::new(),
            borrow_fns: HashSet::new(),
        };
        for item in items {
            ctx.collect_item(item);
        }
        ctx
    }

    fn collect_item(&mut self, item: &Item) {
        match item {
            Item::Struct(def) => {
                self.type_defs.insert(
                    def.name.clone(),
                    TypeDef {
                        generics: def.generics.iter().map(|g| g.name.clone()).collect(),
                        kind: TypeDefKind::Struct(
                            def.fields
                                .iter()
                                .map(|f| FieldInfo {
                                    name: f.name.clone(),
                                    ty: f.ty.clone(),
                                })
                                .collect(),
                        ),
                    },
                );
            }
            Item::Enum(def) => {
                for v in &def.variants {
                    self.insert_variant_owner(&v.name, &def.name);
                }
                self.type_defs.insert(
                    def.name.clone(),
                    TypeDef {
                        generics: def.generics.iter().map(|g| g.name.clone()).collect(),
                        kind: TypeDefKind::Enum(
                            def.variants
                                .iter()
                                .map(|v| VariantInfo {
                                    name: v.name.clone(),
                                    fields: v.data.clone().unwrap_or_default(),
                                })
                                .collect(),
                        ),
                    },
                );
            }
            Item::TypeAlias(_) => {}
            Item::Function(f) => {
                self.fn_sigs.insert(
                    f.name.clone(),
                    (
                        f.generics.clone(),
                        f.params.iter().map(|p| p.ty.clone()).collect(),
                        f.return_type.clone(),
                    ),
                );
            }
            _ => {}
        }
    }

    fn insert_variant_owner(&mut self, variant_name: &str, owner_name: &str) {
        self.variant_owners
            .entry(variant_name.to_string())
            .and_modify(|existing| {
                if existing.as_deref() != Some(owner_name) {
                    *existing = None;
                }
            })
            .or_insert_with(|| Some(owner_name.to_string()));
    }
}

fn candidate_borrow_positions(f: &FunctionDef) -> Vec<usize> {
    f.params
        .iter()
        .enumerate()
        .filter(|(_, param)| !matches!(param.ty, Type::Reference(_, _, _)))
        .map(|(i, _)| i)
        .collect()
}

// ── Phase 1: demand analysis ──────────────────────────────────────────────────

impl BorrowContext {
    /// For every top-level function, determine which parameter positions can be
    /// replaced by shared borrows and record them in `self.borrow_positions`.
    fn analyse_all_functions(&mut self, items: &[Item]) {
        let functions: Vec<&FunctionDef> = items
            .iter()
            .filter_map(|item| match item {
                Item::Function(f) => Some(f),
                _ => None,
            })
            .collect();

        self.borrow_positions.clear();
        for f in &functions {
            self.borrow_positions
                .insert(f.name.clone(), candidate_borrow_positions(f));
        }

        loop {
            let mut changed = false;
            let mut next_positions = HashMap::new();

            for f in &functions {
                let previous = self
                    .borrow_positions
                    .get(&f.name)
                    .cloned()
                    .unwrap_or_default();
                let mut positions = self.borrowable_positions(f);
                positions.retain(|position| previous.contains(position));

                if positions != previous {
                    changed = true;
                }
                next_positions.insert(f.name.clone(), positions);
            }

            self.borrow_positions = next_positions;
            if !changed {
                break;
            }
        }

        self.borrow_positions
            .retain(|_, positions| !positions.is_empty());
    }

    /// Returns the sorted list of parameter indices that are borrowable for `f`.
    fn borrowable_positions(&self, f: &FunctionDef) -> Vec<usize> {
        let copy_generics = generic_names_with_bound(f, "Copy");
        let base_env = function_type_env(f);

        f.params
            .iter()
            .enumerate()
            .filter(|(_, param)| {
                // Only consider owned (non-reference) parameters.
                !matches!(param.ty, Type::Reference(_, _, _))
                    && self.is_param_borrowable(f, param, &base_env, &copy_generics)
            })
            .map(|(i, _)| i)
            .collect()
    }

    /// Checks `Borrowable_Γ(f, x)` from the paper:
    ///   Dem_Γ(f, x) ⊆ {Obs, Bor, Own}  ∧  OwnOK_Γ(f, x)
    ///
    /// OwnOK requires every `Own` demand to come from a source that can produce
    /// an owned value from a shared borrow: either an explicit `.clone()` in the
    /// generated source or a direct Copy use.
    fn is_param_borrowable(
        &self,
        f: &FunctionDef,
        param: &Param,
        base_env: &TypeEnv,
        copy_generics: &HashSet<String>,
    ) -> bool {
        let mut derived: HashSet<String> = HashSet::new();
        derived.insert(param.name.clone());

        let mut demands: HashSet<Demand> = HashSet::new();
        let mut env = base_env.clone();

        self.collect_demands_block(
            &f.body,
            &derived,
            &mut env,
            copy_generics,
            &mut demands,
            true, // tail of the function body is the return value
        );

        // The parameter is borrowable iff no escaping borrow was found and
        // every owned demand can be discharged locally from the borrowed origin.
        !demands.iter().any(|d| is_blocking(*d)) && own_ok(&demands)
    }

    /// Walk a block and collect ownership demands imposed on the derived set.
    fn collect_demands_block(
        &self,
        block: &Block,
        derived: &HashSet<String>,
        env: &mut TypeEnv,
        copy_generics: &HashSet<String>,
        demands: &mut HashSet<Demand>,
        in_return_ctx: bool,
    ) {
        for stmt in &block.stmts {
            match stmt {
                Statement::Let(let_stmt) => {
                    if let Some(init) = &let_stmt.init {
                        // The init expression is in own context (assigned to a binding).
                        self.collect_demands_for_own_arg(
                            init,
                            derived,
                            env,
                            copy_generics,
                            demands,
                        );
                    }
                    // Update env for subsequent statements.
                    let inferred_ty = let_stmt
                        .ty
                        .clone()
                        .or_else(|| {
                            let_stmt
                                .init
                                .as_ref()
                                .and_then(|e| self.infer_type(e, env))
                        });
                    if let Some(ty) = inferred_ty {
                        if is_binding_ident(&let_stmt.name) {
                            // A direct `let y = x` is an owned use.  The demand was already
                            // recorded above, so we do not propagate derivedness through `y`.
                            env.insert(let_stmt.name.clone(), ty);
                        } else {
                            self.bind_pattern_env(&let_stmt.name, &ty, env);
                        }
                    }
                }
                Statement::Expr(expr) => {
                    self.collect_demands_expr(
                        expr,
                        derived,
                        env,
                        copy_generics,
                        demands,
                        false,
                    );
                }
                Statement::Item(_) | Statement::Continue | Statement::Break
                | Statement::Comment(_) => {}
            }
        }

        if let Some(tail) = &block.expr {
            self.collect_demands_expr(
                tail,
                derived,
                env,
                copy_generics,
                demands,
                in_return_ctx,
            );
        }
    }

    /// Walk an expression and collect demands imposed on the derived set.
    fn collect_demands_expr(
        &self,
        expr: &Expr,
        derived: &HashSet<String>,
        env: &mut TypeEnv,
        copy_generics: &HashSet<String>,
        demands: &mut HashSet<Demand>,
        in_return_ctx: bool,
    ) {
        match expr {
            // ── Ident: a direct use of a variable ────────────────────────────
            Expr::Ident(name) => {
                if derived.contains(name) {
                    let ty = env.get(name);
                    if in_return_ctx {
                        // Returning a derived value directly.
                        if ty.map(|t| self.is_copy(t, copy_generics)).unwrap_or(false) {
                            // Copy types can be implicitly copied.
                            demands.insert(Demand::Own(OwnUse::CopyUse));
                        } else {
                            // Non-Copy direct return lacks clone/copy evidence.
                            demands.insert(Demand::Own(OwnUse::DirectOwned));
                        }
                    }
                    // In non-return context an Ident on its own may just be
                    // bound in a pattern or passed around; Own is determined
                    // by the enclosing call/constructor, handled in Call below.
                }
            }

            // ── MethodCall: x.clone() / x.as_ref() / x.method() ─────────────
            Expr::MethodCall(receiver, method, args) => {
                match method.as_str() {
                    "clone" if args.is_empty() => {
                        if let Expr::Ident(name) = receiver.as_ref() {
                            if derived.contains(name) {
                                // `x.clone()` → Own demand (satisfiable via Clone).
                                demands.insert(Demand::Own(OwnUse::ExplicitClone));
                                return;
                            }
                        }
                        // Clone on a non-derived receiver: just recurse.
                        self.collect_demands_expr(
                            receiver,
                            derived,
                            env,
                            copy_generics,
                            demands,
                            false,
                        );
                    }
                    "as_ref" if args.is_empty() => {
                        if let Expr::Ident(name) = receiver.as_ref() {
                            if derived.contains(name) {
                                demands.insert(Demand::Bor);
                                return;
                            }
                        }
                        self.collect_demands_expr(
                            receiver,
                            derived,
                            env,
                            copy_generics,
                            demands,
                            false,
                        );
                    }
                    _ => {
                        let uses_derived = expr_has_free_var_from(receiver, derived)
                            || args.iter().any(|arg| expr_has_free_var_from(arg, derived));
                        self.collect_demands_expr(
                            receiver,
                            derived,
                            env,
                            copy_generics,
                            demands,
                            false,
                        );
                        for arg in args {
                            self.collect_demands_expr(
                                arg,
                                derived,
                                env,
                                copy_generics,
                                demands,
                                false,
                            );
                        }
                        // Unknown method calls have receiver/argument ownership
                        // semantics outside the current model.
                        if uses_derived {
                            demands.insert(Demand::Unk);
                        }
                    }
                }
            }

            // ── Call: f(e1, …, en) ───────────────────────────────────────────
            Expr::Call(callee, args) => {
                self.collect_demands_expr(callee, derived, env, copy_generics, demands, false);

                for (j, arg) in args.iter().enumerate() {
                    // Determine whether position j takes an owned or borrowed arg.
                    let callee_name = callee_fn_name(callee);
                    let borrow_pos = callee_name
                        .and_then(|n| self.borrow_positions.get(n))
                        .map(|positions| positions.contains(&j))
                        .unwrap_or(false);

                    if borrow_pos {
                        // The callee accepts a shared borrow at this position.
                        // Any use of the derived var here is a Bor demand.
                        self.collect_demands_for_bor_arg(arg, derived, env, copy_generics, demands);
                    } else {
                        // Owned argument: derived variables must be moved or cloned.
                        self.collect_demands_for_own_arg(arg, derived, env, copy_generics, demands);
                    }
                }
            }

            // ── Match: match e { arms } ──────────────────────────────────────
            Expr::Match { expr: scrutinee, arms } => {
                // Isabelle's code generator wraps multi-parameter functions in a
                // tuple match: `match (x, y) { (p1, p2) => body }`.  The tuple
                // construction is an ownership-passing artefact, not a direct
                // ownership demand on the whole tuple:
                // the ownership flows directly into the pattern-bound variables.
                // We detect this case and propagate the derived set through the
                // tuple positions instead of recording a spurious whole-tuple demand.
                let is_tuple_scrutinee = matches!(scrutinee.as_ref(), Expr::Tuple(_));

                if !is_tuple_scrutinee {
                    // The scrutinee is inspected (Obs), not consumed.
                    if let Expr::Ident(name) = scrutinee.as_ref() {
                        if derived.contains(name) {
                            demands.insert(Demand::Obs);
                        }
                    }
                    self.collect_demands_expr(
                        scrutinee,
                        derived,
                        env,
                        copy_generics,
                        demands,
                        false,
                    );
                } else {
                    // Tuple scrutinee: only analyze non-derived elements.
                    // Derived idents in the tuple are handled via pattern propagation.
                    if let Expr::Tuple(elems) = scrutinee.as_ref() {
                        for elem in elems {
                            if let Expr::Ident(name) = elem {
                                if derived.contains(name) {
                                    continue; // demand tracked via arm pattern
                                }
                            }
                            self.collect_demands_expr(elem, derived, env, copy_generics, demands, false);
                        }
                    }
                }

                let scrutinee_ty = self.infer_type(scrutinee, env);

                for arm in arms {
                    let mut arm_env = env.clone();
                    let mut arm_derived = derived.clone();

                    if let Some(ty) = &scrutinee_ty {
                        self.bind_pattern_env(&arm.pattern, ty, &mut arm_env);
                        // Variables bound in the pattern are derived if the
                        // scrutinee expression is derived.
                        if let Expr::Ident(sname) = scrutinee.as_ref() {
                            if derived.contains(sname) {
                                self.collect_derived_from_pattern(
                                    &arm.pattern,
                                    ty,
                                    &mut arm_derived,
                                );
                            }
                        } else if is_tuple_scrutinee {
                            // Propagate derived set through tuple positions.
                            // collect_derived_from_pattern handles tuple patterns
                            // when ty is Type::Tuple — we always invoke it here
                            // (it is a no-op when the pattern has no ident bindings).
                            self.collect_derived_from_pattern(
                                &arm.pattern,
                                ty,
                                &mut arm_derived,
                            );
                        }
                    }

                    if let Some(guard) = &arm.guard {
                        self.collect_demands_expr(
                            guard,
                            &arm_derived,
                            &mut arm_env,
                            copy_generics,
                            demands,
                            false,
                        );
                    }
                    self.collect_demands_block(
                        &arm.body,
                        &arm_derived,
                        &mut arm_env,
                        copy_generics,
                        demands,
                        in_return_ctx,
                    );
                }
            }

            // ── Reference: &e ────────────────────────────────────────────────
            Expr::Reference(inner, true, false) => {
                // &derived_var  → Bor demand (shared borrow, not escape).
                if let Expr::Ident(name) = inner.as_ref() {
                    if derived.contains(name) {
                        demands.insert(Demand::Bor);
                        return;
                    }
                }
                self.collect_demands_expr(inner, derived, env, copy_generics, demands, false);
            }

            // ── &mut: outside the current Isabelle2Rust borrow model ───────────
            Expr::Reference(inner, true, true) => {
                if expr_has_free_var_from(inner, derived) {
                    demands.insert(Demand::Unk);
                }
            }

            // ── Tuple ────────────────────────────────────────────────────────
            Expr::Tuple(elems) => {
                for e in elems {
                    // Tuple fields are own positions (ownership is bundled).
                    self.collect_demands_for_own_arg(e, derived, env, copy_generics, demands);
                }
            }

            // ── Block ────────────────────────────────────────────────────────
            Expr::Block(block) => {
                let mut block_env = env.clone();
                self.collect_demands_block(
                    block,
                    derived,
                    &mut block_env,
                    copy_generics,
                    demands,
                    in_return_ctx,
                );
            }

            // ── If / IfLet ───────────────────────────────────────────────────
            Expr::If {
                condition,
                then_branch,
                else_branch,
            } => {
                self.collect_demands_expr(condition, derived, env, copy_generics, demands, false);
                let mut then_env = env.clone();
                self.collect_demands_block(
                    then_branch,
                    derived,
                    &mut then_env,
                    copy_generics,
                    demands,
                    in_return_ctx,
                );
                if let Some(eb) = else_branch {
                    let mut else_env = env.clone();
                    self.collect_demands_block(
                        eb,
                        derived,
                        &mut else_env,
                        copy_generics,
                        demands,
                        in_return_ctx,
                    );
                }
            }
            Expr::IfLet {
                pattern,
                value,
                then_branch,
                else_branch,
            } => {
                self.collect_demands_expr(value, derived, env, copy_generics, demands, false);
                let mut then_env = env.clone();
                if let Some(ty) = self.infer_type(value, env) {
                    self.bind_pattern_env(pattern, &ty, &mut then_env);
                }
                self.collect_demands_block(
                    then_branch,
                    derived,
                    &mut then_env,
                    copy_generics,
                    demands,
                    in_return_ctx,
                );
                if let Some(eb) = else_branch {
                    let mut else_env = env.clone();
                    self.collect_demands_block(
                        eb,
                        derived,
                        &mut else_env,
                        copy_generics,
                        demands,
                        in_return_ctx,
                    );
                }
            }

            Expr::Parenthesized(inner) => {
                self.collect_demands_expr(inner, derived, env, copy_generics, demands, in_return_ctx);
            }
            Expr::BinaryOp(l, _, r) => {
                self.collect_demands_expr(l, derived, env, copy_generics, demands, false);
                self.collect_demands_expr(r, derived, env, copy_generics, demands, false);
            }
            Expr::UnaryOp(_, inner) => {
                self.collect_demands_expr(inner, derived, env, copy_generics, demands, false);
            }

            // Closure: only generate a demand if a derived variable appears
            // free in the closure body (not shadowed by the closure's own params).
            // For `move` closures the capture is an owned demand; for non-move it
            // is an escaping borrow.
            // The owncap pattern (`let y_cap = y.clone()` + `move |…| {…y_cap…}`)
            // does NOT capture `y` directly — only `y_cap` — so derived vars
            // for `y` don't appear free and no blocking demand is generated.
            Expr::Closure(params, body, is_move) => {
                let shadowed: HashSet<String> = params
                    .iter()
                    .map(|p| closure_param_name(p))
                    .collect();
                let outer_derived: HashSet<String> =
                    derived.difference(&shadowed).cloned().collect();
                if !outer_derived.is_empty()
                    && expr_has_free_var_from(body, &outer_derived)
                {
                    if *is_move {
                        demands.insert(Demand::Own(OwnUse::DirectOwned));
                    } else {
                        demands.insert(Demand::Esc);
                    }
                }
            }
            Expr::Path(_, _) | Expr::Literal(_) => {}
            Expr::Loop(block) | Expr::Unsafe(block) => {
                if block_has_free_var_from(block, derived) {
                    demands.insert(Demand::Unk);
                }
            }
            Expr::Await(inner) => {
                if expr_has_free_var_from(inner, derived) {
                    demands.insert(Demand::Unk);
                }
            }
            Expr::BuilderChain(methods) => {
                if builder_chain_has_free_var_from(methods, derived) {
                    demands.insert(Demand::Unk);
                }
            }
            Expr::Index(base, index) | Expr::Assign(base, index) => {
                if expr_has_free_var_from(base, derived) || expr_has_free_var_from(index, derived)
                {
                    demands.insert(Demand::Unk);
                }
            }
            Expr::Reference(inner, _, _) => {
                if expr_has_free_var_from(inner, derived) {
                    demands.insert(Demand::Unk);
                }
            }
        }
    }

    /// Collect demands for an expression used in an *own* (ownership-consuming)
    /// argument position (e.g., a constructor field or a non-borrow callee).
    fn collect_demands_for_own_arg(
        &self,
        arg: &Expr,
        derived: &HashSet<String>,
        env: &mut TypeEnv,
        copy_generics: &HashSet<String>,
        demands: &mut HashSet<Demand>,
    ) {
        match arg {
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                if let Expr::Ident(name) = receiver.as_ref() {
                    if derived.contains(name) {
                        // `x.clone()` in own position → Own demand (satisfiable).
                        demands.insert(Demand::Own(OwnUse::ExplicitClone));
                        return;
                    }
                }
                self.collect_demands_expr(arg, derived, env, copy_generics, demands, false);
            }
            Expr::Ident(name) => {
                if derived.contains(name) {
                    let ty = env.get(name);
                    if ty.map(|t| self.is_copy(t, copy_generics)).unwrap_or(false) {
                        // Copy type: direct use is an implicit copy – Own demand.
                        demands.insert(Demand::Own(OwnUse::CopyUse));
                    } else {
                        // Non-Copy type passed directly without clone lacks
                        // clone/copy evidence.
                        demands.insert(Demand::Own(OwnUse::DirectOwned));
                    }
                } else {
                    self.collect_demands_expr(arg, derived, env, copy_generics, demands, false);
                }
            }
            _ => {
                self.collect_demands_expr(arg, derived, env, copy_generics, demands, false);
            }
        }
    }

    /// Collect demands for an expression that goes into a *bor*
    /// (shared-borrow) argument position.
    fn collect_demands_for_bor_arg(
        &self,
        arg: &Expr,
        derived: &HashSet<String>,
        env: &mut TypeEnv,
        copy_generics: &HashSet<String>,
        demands: &mut HashSet<Demand>,
    ) {
        // In a bor position a `.clone()` of a derived var becomes `.as_ref()` or
        // the variable itself, so it is a Bor demand.
        match arg {
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                if let Expr::Ident(name) = receiver.as_ref() {
                    if derived.contains(name) {
                        demands.insert(Demand::Bor);
                        return;
                    }
                }
                self.collect_demands_expr(arg, derived, env, copy_generics, demands, false);
            }
            Expr::Ident(name) if derived.contains(name) => {
                demands.insert(Demand::Bor);
            }
            _ => {
                self.collect_demands_expr(arg, derived, env, copy_generics, demands, false);
            }
        }
    }

    /// Extend `derived` with the variables bound by `pattern` matching `ty`.
    fn collect_derived_from_pattern(
        &self,
        pattern: &str,
        ty: &Type,
        derived: &mut HashSet<String>,
    ) {
        let pattern = pattern.trim();
        if pattern.is_empty() || pattern == "_" || pattern == ".." {
            return;
        }

        // Strip `box` prefix – both the binding and its inner content are derived.
        if let Some(inner) = strip_prefix_word(pattern, "box") {
            self.collect_derived_from_pattern(inner, ty, derived);
            return;
        }

        let pattern = strip_binding_modifiers(pattern);

        // Tuple pattern: (p1, p2, …)
        if let Some(inner) = outer_parens_inner(pattern) {
            let parts = split_top_level_commas(inner);
            if parts.len() > 1 {
                if let Type::Tuple(types) = ty {
                    for (p, t) in parts.iter().zip(types) {
                        self.collect_derived_from_pattern(p, t, derived);
                    }
                }
                return;
            }
        }

        // Constructor pattern: K(p1, p2, …)
        if let Some((constructor, args)) = split_constructor_pattern(pattern) {
            if let Some(field_types) = self.pattern_field_types(constructor, ty) {
                for (arg, fty) in args.iter().zip(field_types.iter()) {
                    self.collect_derived_from_pattern(arg, fty, derived);
                }
            }
            return;
        }

        if pattern.contains("::") || matches!(pattern, "true" | "false") {
            return;
        }

        if is_binding_ident(pattern) {
            derived.insert(pattern.to_string());
        }
    }
}

// ── Phase 2/3: rewrite signatures and bodies in place ────────────────────────

impl BorrowContext {
    fn rewrite_all_signatures_in_place(&mut self, items: &mut [Item]) {
        for item in items {
            if let Item::Function(f) = item {
                self.rewrite_signature_in_place(f);
            }
        }
    }

    fn rewrite_signature_in_place(&mut self, f: &mut FunctionDef) {
        let Some(positions) = self.borrow_positions.get(&f.name).cloned() else {
            return;
        };
        if positions.is_empty() {
            return;
        }

        for (i, param) in f.params.iter_mut().enumerate() {
            if positions.contains(&i) && !is_reference_type(&param.ty) {
                param.ty = make_ref_type(&param.ty);
            }
        }

        ensure_function_comment(f, "// borrow-optimized by shared parameters");
        self.borrow_fns.insert(f.name.clone());
    }

    fn rewrite_all_bodies_and_calls_in_place(&self, items: &mut [Item]) {
        for item in items {
            if let Item::Function(f) = item {
                self.rewrite_function_body_in_place(f);
            }
        }
    }

    fn rewrite_function_body_in_place(&self, f: &mut FunctionDef) {
        let mut borrow_env = function_type_env(f);
        let orig_env = self.original_function_type_env(f);
        let copy_generics = generic_names_with_bound(f, "Copy");
        f.body = self.rewrite_block_borrow(
            &f.body,
            &mut borrow_env,
            &orig_env,
            &copy_generics,
            &f.name,
        );
    }

    fn original_function_type_env(&self, f: &FunctionDef) -> TypeEnv {
        let Some((_, param_types, _)) = self.fn_sigs.get(&f.name) else {
            return function_type_env(f);
        };

        f.params
            .iter()
            .zip(param_types.iter())
            .filter(|(param, _)| !param.name.is_empty())
            .map(|(param, ty)| (param.name.clone(), ty.clone()))
            .collect()
    }

    // ── Body rewriter ─────────────────────────────────────────────────────────

    fn rewrite_block_borrow(
        &self,
        block: &Block,
        borrow_env: &mut BorrowEnv,
        orig_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        orig_fn_name: &str,
    ) -> Block {
        let mut stmts = Vec::new();
        let mut local_orig = orig_env.clone();

        for (stmt_idx, stmt) in block.stmts.iter().enumerate() {
            match stmt {
                Statement::Let(let_stmt) => {
                    // B-Closure: try to eliminate the owncap wrapper before
                    // falling through to the general own-rewrite.
                    // The binding must be used only as a local direct callee;
                    // returned/stored/passed/captured closures retain `move`.
                    let bclosure = if is_binding_ident(&let_stmt.name)
                        && closure_binding_is_nonescaping_use(block, stmt_idx, &let_stmt.name)
                    {
                        let_stmt.init.as_ref().and_then(|init| {
                            self.try_bclosure_rewrite(init, &local_orig, copy_generics)
                        })
                    } else {
                        None
                    };
                    let new_init = if let Some(closure_expr) = bclosure {
                        Some(closure_expr)
                    } else {
                        let_stmt.init.as_ref().map(|init| {
                            self.rewrite_expr_own(
                                init,
                                borrow_env,
                                &local_orig,
                                copy_generics,
                                orig_fn_name,
                            )
                        })
                    };
                    // Update environments.
                    if let Some(ty) = let_stmt
                        .ty
                        .clone()
                        .or_else(|| {
                            let_stmt
                                .init
                                .as_ref()
                                .and_then(|e| self.infer_type(e, &local_orig))
                        })
                    {
                        if is_binding_ident(&let_stmt.name) {
                            local_orig.insert(let_stmt.name.clone(), ty.clone());
                            borrow_env.insert(let_stmt.name.clone(), ty);
                        } else {
                            self.bind_pattern_env(&let_stmt.name, &ty, &mut local_orig);
                            self.bind_pattern_env_for_borrow(&let_stmt.name, &ty, borrow_env);
                        }
                    }
                    stmts.push(Statement::Let(LetStmt {
                        ifmut: let_stmt.ifmut,
                        name: let_stmt.name.clone(),
                        ty: let_stmt.ty.clone(),
                        init: new_init,
                    }));
                }
                Statement::Expr(expr) => {
                    stmts.push(Statement::Expr(self.rewrite_expr_own(
                        expr,
                        borrow_env,
                        &local_orig,
                        copy_generics,
                        orig_fn_name,
                    )));
                }
                Statement::Item(item) => stmts.push(Statement::Item(item.clone())),
                Statement::Continue => stmts.push(Statement::Continue),
                Statement::Break => stmts.push(Statement::Break),
                Statement::Comment(c) => stmts.push(Statement::Comment(c.clone())),
            }
        }

        let tail = block.expr.as_ref().map(|e| {
            Box::new(self.rewrite_expr_own(
                e,
                borrow_env,
                &local_orig,
                copy_generics,
                orig_fn_name,
            ))
        });

        Block { stmts, expr: tail }
    }

    /// Rewrite `expr` for an **own** (ownership-consuming) context.
    fn rewrite_expr_own(
        &self,
        expr: &Expr,
        borrow_env: &BorrowEnv,
        orig_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        orig_fn_name: &str,
    ) -> Expr {
        match expr {
            // ── Direct use of a borrowed variable in own context ──────────────
            Expr::Ident(name) => {
                if let Some(bty) = borrow_env.get(name) {
                    if is_reference_type(bty) {
                        // &T in own context: deref-copy if Copy, else clone.
                        let inner = ref_inner(bty);
                        if self.is_copy(inner.unwrap_or(bty), copy_generics) {
                            return Expr::UnaryOp(
                                "*".to_string(),
                                Box::new(Expr::Ident(name.clone())),
                            );
                        } else {
                            return Expr::MethodCall(
                                Box::new(Expr::Ident(name.clone())),
                                "clone".to_string(),
                                vec![],
                            );
                        }
                    }
                }
                expr.clone()
            }

            // ── Clone in own context: transform based on the receiver's type ──
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                if let Expr::Ident(name) = receiver.as_ref() {
                    if let Some(bty) = borrow_env.get(name) {
                        if is_reference_type(bty) {
                            let inner = ref_inner(bty);
                            return if is_box_type(inner.unwrap_or(bty)) {
                                // &Box<T>.clone() in own context: produce Box<T> via
                                // `v.as_ref().clone()` which gives T is NOT right…
                                // Actually we want Box<T>: just v.clone() is fine.
                                // But in generated code the original `xs` was the inner T
                                // after box pattern, so `xs.clone()` was T.
                                // In the rewritten body xs: &Box<T>, own needs T → as_ref().clone()
                                let as_ref_call = Expr::MethodCall(
                                    Box::new(Expr::Ident(name.clone())),
                                    "as_ref".to_string(),
                                    vec![],
                                );
                                Expr::MethodCall(
                                    Box::new(as_ref_call),
                                    "clone".to_string(),
                                    vec![],
                                )
                            } else {
                                // &T.clone() in own context → v.clone() (gives T)
                                Expr::MethodCall(
                                    Box::new(Expr::Ident(name.clone())),
                                    "clone".to_string(),
                                    vec![],
                                )
                            };
                        }
                    }
                }
                // Recurse into non-borrowed receiver.
                Expr::MethodCall(
                    Box::new(self.rewrite_expr_own(
                        receiver, borrow_env, orig_env, copy_generics, orig_fn_name,
                    )),
                    method.clone(),
                    args.iter()
                        .map(|a| {
                            self.rewrite_expr_own(a, borrow_env, orig_env, copy_generics, orig_fn_name)
                        })
                        .collect(),
                )
            }

            // ── Call: adapt arguments to the callee's final parameter mode ────
            Expr::Call(callee, args) => {
                let fn_name = callee_fn_name(callee);

                if let Some(borrow_positions) = fn_name.and_then(|name| {
                    self.borrow_positions.get(name).filter(|positions| !positions.is_empty())
                }) {
                    let new_callee = callee.as_ref().clone();
                    let new_args: Vec<Expr> = args
                        .iter()
                        .enumerate()
                        .map(|(j, arg)| {
                            if borrow_positions.contains(&j) {
                                // B-Call bor position: prepare a shared argument.
                                self.bor_transform(arg, borrow_env, orig_env, copy_generics, orig_fn_name)
                            } else {
                                // Own position: preserve owned semantics.
                                self.rewrite_expr_own(
                                    arg, borrow_env, orig_env, copy_generics, orig_fn_name,
                                )
                            }
                        })
                        .collect();
                    return Expr::Call(Box::new(new_callee), new_args);
                }

                // Callee has no borrowed parameters: all args are own positions.
                // A direct call of an owncap closure is call-local, so B-Closure
                // can safely remove the owned capture wrapper here.
                let new_callee = self
                    .try_bclosure_rewrite(callee, orig_env, copy_generics)
                    .unwrap_or_else(|| {
                        self.rewrite_expr_own(
                            callee,
                            borrow_env,
                            orig_env,
                            copy_generics,
                            orig_fn_name,
                        )
                    });
                let new_args = args
                    .iter()
                    .map(|a| {
                        self.rewrite_expr_own(a, borrow_env, orig_env, copy_generics, orig_fn_name)
                    })
                    .collect();
                Expr::Call(Box::new(new_callee), new_args)
            }

            // ── Match: B-Match rule ───────────────────────────────────────────
            Expr::Match { expr: scrutinee, arms } => {
                // For a borrowed scrutinee keep it as-is: Rust match ergonomics
                // handles matching on `&T` with plain `T` patterns.  Calling
                // rewrite_expr_own would wrongly insert a `.clone()`.
                let scrutinee_borrow_type = match scrutinee.as_ref() {
                    Expr::Ident(name) => borrow_env.get(name).cloned(),
                    _ => None,
                };
                let scrutinee_is_borrowed = scrutinee_borrow_type
                    .as_ref()
                    .map(is_reference_type)
                    .unwrap_or(false);

                let new_scrutinee = if scrutinee_is_borrowed {
                    scrutinee.as_ref().clone()
                } else {
                    self.rewrite_expr_own(
                        scrutinee, borrow_env, orig_env, copy_generics, orig_fn_name,
                    )
                };

                let new_arms: Vec<MatchArm> = arms
                    .iter()
                    .map(|arm| {
                        let mut arm_borrow = borrow_env.clone();
                        let mut arm_orig = orig_env.clone();
                        let new_pattern;

                        if scrutinee_is_borrowed {
                            // B-Match: strip `box` from patterns; field variables
                            // get type `&F_j` (reference to the original field type).
                            let inner_ty = ref_inner(scrutinee_borrow_type.as_ref().unwrap())
                                .cloned()
                                .unwrap_or_else(|| scrutinee_borrow_type.clone().unwrap());

                            // Compute field types for this constructor from the
                            // inner (non-reference) scrutinee type.
                            self.bind_pattern_env_for_borrow_match(
                                &arm.pattern,
                                &inner_ty,
                                &mut arm_borrow,
                            );
                            self.bind_pattern_env(&arm.pattern, &inner_ty, &mut arm_orig);

                            // Strip `box` from the pattern string.
                            new_pattern = strip_box_from_pattern(&arm.pattern);
                        } else {
                            // Non-borrowed scrutinee: pattern unchanged.
                            if let Some(ty) = self.infer_type(scrutinee, orig_env) {
                                self.bind_pattern_env(&arm.pattern, &ty, &mut arm_orig);
                                self.bind_pattern_env_for_borrow(&arm.pattern, &ty, &mut arm_borrow);
                            }
                            new_pattern = arm.pattern.clone();
                        }

                        let new_guard =
                            arm.guard.as_ref().map(|g| {
                                self.rewrite_expr_own(
                                    g, &arm_borrow, &arm_orig, copy_generics, orig_fn_name,
                                )
                            });
                        let new_body = self.rewrite_block_borrow(
                            &arm.body,
                            &mut arm_borrow,
                            &arm_orig,
                            copy_generics,
                            orig_fn_name,
                        );

                        MatchArm {
                            pattern: new_pattern,
                            guard: new_guard,
                            body: new_body,
                        }
                    })
                    .collect();

                Expr::Match {
                    expr: Box::new(new_scrutinee),
                    arms: new_arms,
                }
            }

            // ── Block ─────────────────────────────────────────────────────────
            Expr::Block(block) => {
                let mut inner_borrow = borrow_env.clone();
                Expr::Block(self.rewrite_block_borrow(
                    block,
                    &mut inner_borrow,
                    orig_env,
                    copy_generics,
                    orig_fn_name,
                ))
            }

            // ── Tuple ─────────────────────────────────────────────────────────
            Expr::Tuple(elems) => Expr::Tuple(
                elems
                    .iter()
                    .map(|e| {
                        self.rewrite_expr_own(e, borrow_env, orig_env, copy_generics, orig_fn_name)
                    })
                    .collect(),
            ),

            // ── Reference ────────────────────────────────────────────────────
            Expr::Reference(inner, is_ref, is_mut) => Expr::Reference(
                Box::new(self.rewrite_expr_own(
                    inner, borrow_env, orig_env, copy_generics, orig_fn_name,
                )),
                *is_ref,
                *is_mut,
            ),

            // ── If ────────────────────────────────────────────────────────────
            Expr::If {
                condition,
                then_branch,
                else_branch,
            } => {
                let new_cond = self.rewrite_expr_own(
                    condition, borrow_env, orig_env, copy_generics, orig_fn_name,
                );
                let mut then_borrow = borrow_env.clone();
                let new_then = self.rewrite_block_borrow(
                    then_branch, &mut then_borrow, orig_env, copy_generics, orig_fn_name,
                );
                let new_else = else_branch.as_ref().map(|eb| {
                    let mut else_borrow = borrow_env.clone();
                    self.rewrite_block_borrow(
                        eb, &mut else_borrow, orig_env, copy_generics, orig_fn_name,
                    )
                });
                Expr::If {
                    condition: Box::new(new_cond),
                    then_branch: new_then,
                    else_branch: new_else,
                }
            }

            Expr::IfLet {
                pattern,
                value,
                then_branch,
                else_branch,
            } => {
                let new_value = self.rewrite_expr_own(
                    value, borrow_env, orig_env, copy_generics, orig_fn_name,
                );
                let mut then_borrow = borrow_env.clone();
                let new_then = self.rewrite_block_borrow(
                    then_branch, &mut then_borrow, orig_env, copy_generics, orig_fn_name,
                );
                let new_else = else_branch.as_ref().map(|eb| {
                    let mut else_borrow = borrow_env.clone();
                    self.rewrite_block_borrow(
                        eb, &mut else_borrow, orig_env, copy_generics, orig_fn_name,
                    )
                });
                Expr::IfLet {
                    pattern: pattern.clone(),
                    value: Box::new(new_value),
                    then_branch: new_then,
                    else_branch: new_else,
                }
            }

            Expr::Parenthesized(inner) => Expr::Parenthesized(Box::new(self.rewrite_expr_own(
                inner, borrow_env, orig_env, copy_generics, orig_fn_name,
            ))),
            Expr::BinaryOp(l, op, r) => Expr::BinaryOp(
                Box::new(self.rewrite_expr_own(l, borrow_env, orig_env, copy_generics, orig_fn_name)),
                op.clone(),
                Box::new(self.rewrite_expr_own(r, borrow_env, orig_env, copy_generics, orig_fn_name)),
            ),
            Expr::UnaryOp(op, inner) => Expr::UnaryOp(
                op.clone(),
                Box::new(self.rewrite_expr_own(
                    inner, borrow_env, orig_env, copy_generics, orig_fn_name,
                )),
            ),
            Expr::MethodCall(receiver, method, args) => Expr::MethodCall(
                Box::new(self.rewrite_expr_own(
                    receiver, borrow_env, orig_env, copy_generics, orig_fn_name,
                )),
                method.clone(),
                args.iter()
                    .map(|a| {
                        self.rewrite_expr_own(a, borrow_env, orig_env, copy_generics, orig_fn_name)
                    })
                    .collect(),
            ),

            // Leaves and unsupported constructs: return unchanged.
            Expr::Path(_, _)
            | Expr::Literal(_)
            | Expr::Loop(_)
            | Expr::Await(_)
            | Expr::Closure(_, _, _)
            | Expr::BuilderChain(_)
            | Expr::Unsafe(_)
            | Expr::Index(_, _)
            | Expr::Assign(_, _) => expr.clone(),
        }
    }

    /// Apply the **bor** transform to `arg`, producing a `&T` for use at a
    /// borrow-positioned call argument (paper §4, B-Call).
    ///
    /// ```text
    /// bor(v.clone())  where v: &Box<T>  →  v.as_ref()
    /// bor(v.clone())  where v: &T       →  v
    /// bor(v)          where v: &T       →  v
    /// bor(v)          where v: T (Copy) →  &v
    /// bor(other)                        →  &other
    /// ```
    fn bor_transform(
        &self,
        arg: &Expr,
        borrow_env: &BorrowEnv,
        orig_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        orig_fn_name: &str,
    ) -> Expr {
        match arg {
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                if let Expr::Ident(name) = receiver.as_ref() {
                    if let Some(bty) = borrow_env.get(name) {
                        if is_reference_type(bty) {
                            let inner = ref_inner(bty);
                            return if is_box_type(inner.unwrap_or(bty)) {
                                // v: &Box<T> → v.as_ref() gives &T
                                Expr::MethodCall(
                                    Box::new(Expr::Ident(name.clone())),
                                    "as_ref".to_string(),
                                    vec![],
                                )
                            } else {
                                // v: &T → v (drop clone)
                                Expr::Ident(name.clone())
                            };
                        }
                    }
                }
                // Recurse and wrap in &.
                let inner = self.rewrite_expr_own(arg, borrow_env, orig_env, copy_generics, orig_fn_name);
                Expr::Reference(Box::new(inner), true, false)
            }
            Expr::Ident(name) => {
                if let Some(bty) = borrow_env.get(name) {
                    if is_reference_type(bty) {
                        // Already a reference: return as-is.
                        return Expr::Ident(name.clone());
                    }
                    // Copy type owned: wrap in &.
                    if self.is_copy(bty, copy_generics) {
                        return Expr::Reference(Box::new(Expr::Ident(name.clone())), true, false);
                    }
                }
                // Non-Copy owned: shouldn't normally arise for a borrowable arg,
                // but fall back to &name conservatively.
                Expr::Reference(Box::new(Expr::Ident(name.clone())), true, false)
            }
            _ => {
                let inner = self.rewrite_expr_own(arg, borrow_env, orig_env, copy_generics, orig_fn_name);
                Expr::Reference(Box::new(inner), true, false)
            }
        }
    }

    // ── Environment helpers ───────────────────────────────────────────────────

    /// Bind pattern variables to their field types in an ordinary TypeEnv.
    fn bind_pattern_env(&self, pattern: &str, expected: &Type, env: &mut TypeEnv) {
        let pattern = pattern.trim();
        if pattern.is_empty() || pattern == "_" || pattern == ".." {
            return;
        }

        if let Some(inner) = strip_prefix_word(pattern, "box") {
            let inner_ty = match expected {
                Type::Generic(name, params) if name == "Box" && params.len() == 1 => &params[0],
                _ => expected,
            };
            self.bind_pattern_env(inner, inner_ty, env);
            return;
        }

        let pattern = strip_binding_modifiers(pattern);

        if let Some(inner) = outer_parens_inner(pattern) {
            let parts = split_top_level_commas(inner);
            if parts.len() > 1 {
                if let Type::Tuple(types) = expected {
                    for (p, t) in parts.iter().zip(types) {
                        self.bind_pattern_env(p, t, env);
                    }
                }
                return;
            }
        }

        if let Some((constructor, args)) = split_constructor_pattern(pattern) {
            if let Some(field_types) = self.pattern_field_types(constructor, expected) {
                for (arg, ty) in args.iter().zip(field_types.iter()) {
                    self.bind_pattern_env(arg, ty, env);
                }
            }
            return;
        }

        if pattern.contains("::") || matches!(pattern, "true" | "false") {
            return;
        }

        if is_binding_ident(pattern) {
            env.insert(pattern.to_string(), expected.clone());
        }
    }

    /// Like `bind_pattern_env` but for a BorrowEnv: each bound variable gets
    /// the same type as in the normal env (no reference wrapping).  Used for
    /// non-borrowed scrutinees.
    fn bind_pattern_env_for_borrow(&self, pattern: &str, expected: &Type, env: &mut BorrowEnv) {
        self.bind_pattern_env(pattern, expected, env);
    }

    /// B-Match rule: bind pattern variables when the scrutinee has type `&D<T>`.
    ///
    /// Each field variable `y_j` gets type `&F_j` (a shared reference to the
    /// field type).  `box y_j` patterns have already been stripped; the stored
    /// type is `&Box<F_inner>` (the original field type wrapped in `&`).
    fn bind_pattern_env_for_borrow_match(
        &self,
        pattern: &str,
        inner_ty: &Type, // inner type D<T> (reference already stripped)
        env: &mut BorrowEnv,
    ) {
        let pattern = pattern.trim();
        if pattern.is_empty() || pattern == "_" || pattern == ".." {
            return;
        }

        // Peel `box` – the variable binds to &Box<T_inner>, not &T_inner.
        // The box is stripped from the pattern string elsewhere; here we just
        // need the correct type.
        if let Some(inner_p) = strip_prefix_word(pattern, "box") {
            // Field type is Box<F>; after stripping box in the pattern the
            // variable binds to &Box<F>.
            let box_ty = inner_ty.clone(); // already Box<F> at this point if called correctly
            env.insert(
                inner_p.trim().to_string(),
                make_ref_type(&box_ty),
            );
            return;
        }

        let pattern = strip_binding_modifiers(pattern);

        if let Some(inner) = outer_parens_inner(pattern) {
            let parts = split_top_level_commas(inner);
            if parts.len() > 1 {
                if let Type::Tuple(types) = inner_ty {
                    for (p, t) in parts.iter().zip(types) {
                        self.bind_pattern_env_for_borrow_match(p, t, env);
                    }
                }
                return;
            }
        }

        if let Some((constructor, args)) = split_constructor_pattern(pattern) {
            if let Some(field_types) = self.pattern_field_types(constructor, inner_ty) {
                for (arg, fty) in args.iter().zip(field_types.iter()) {
                    // Each field variable gets type &F_j (reference to field type).
                    let ref_ty = make_ref_type(fty);
                    let sub_pattern = arg.trim();
                    if let Some(box_inner) = strip_prefix_word(sub_pattern, "box") {
                        // `box y` in the sub-pattern: field is Box<T>, var → &Box<T>
                        let var = strip_binding_modifiers(box_inner.trim());
                        if is_binding_ident(var) {
                            env.insert(var.to_string(), ref_ty);
                        }
                    } else {
                        let var = strip_binding_modifiers(sub_pattern);
                        if var.is_empty() || var == "_" || var == ".." {
                            // nothing
                        } else if is_binding_ident(var) {
                            env.insert(var.to_string(), ref_ty);
                        } else {
                            // Nested constructor pattern: recurse.
                            self.bind_pattern_env_for_borrow_match(var, fty, env);
                        }
                    }
                }
            }
            return;
        }

        if pattern.contains("::") || matches!(pattern, "true" | "false") {
            return;
        }

        if is_binding_ident(pattern) {
            env.insert(pattern.to_string(), make_ref_type(inner_ty));
        }
    }

    // ── Type helpers ──────────────────────────────────────────────────────────

    fn infer_type(&self, expr: &Expr, env: &TypeEnv) -> Option<Type> {
        match expr {
            Expr::Ident(name) => env.get(name).cloned(),
            Expr::Literal(Literal::Bool(_)) => Some(Type::Named("bool".to_string())),
            Expr::Tuple(elems) => {
                let types: Option<Vec<_>> = elems.iter().map(|e| self.infer_type(e, env)).collect();
                types.map(|ts| if ts.is_empty() { Type::Unit } else { Type::Tuple(ts) })
            }
            Expr::Call(callee, _) => match callee.as_ref() {
                Expr::Ident(name) => {
                    self.owner_for_variant_name(name)
                        .map(Type::Named)
                        .or_else(|| {
                            self.fn_sigs.get(name).map(|(_, _, ret)| ret.clone())
                        })
                }
                Expr::Path(path, PathType::Namespace) => path
                    .last()
                    .and_then(|name| {
                        self.owner_for_variant_name(name)
                            .map(Type::Named)
                            .or_else(|| {
                                self.fn_sigs.get(name).map(|(_, _, ret)| ret.clone())
                            })
                    }),
                _ => None,
            },
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                // `v.clone()` where v: &T gives T (auto-deref clone).
                self.infer_type(receiver, env).map(|ty| {
                    if let Type::Reference(inner, true, false) = ty {
                        *inner
                    } else {
                        ty
                    }
                })
            }
            Expr::Parenthesized(inner) => self.infer_type(inner, env),
            Expr::Block(block) => block
                .expr
                .as_ref()
                .and_then(|e| self.infer_type(e, env)),
            _ => None,
        }
    }

    /// Returns the field types for constructor `constructor` applied to `ty`.
    fn pattern_field_types(&self, constructor: &str, ty: &Type) -> Option<Vec<Type>> {
        let variant_name = constructor
            .rsplit("::")
            .next()
            .unwrap_or(constructor)
            .trim();

        if let Some(type_name) = local_type_name(ty) {
            if let Some(def) = self.type_defs.get(type_name) {
                let subst = type_substitution(def, ty);
                match &def.kind {
                    TypeDefKind::Enum(variants) => {
                        if let Some(v) = variants.iter().find(|v| v.name == variant_name) {
                            return Some(
                                v.fields
                                    .iter()
                                    .map(|f| apply_type_subst(f, &subst))
                                    .collect(),
                            );
                        }
                    }
                    TypeDefKind::Struct(fields)
                        if variant_name == type_name || constructor.trim() == type_name =>
                    {
                        return Some(
                            fields.iter().map(|f| apply_type_subst(&f.ty, &subst)).collect(),
                        );
                    }
                    TypeDefKind::Struct(_) => {}
                }
            }
        }

        // Try via variant owner map.
        let owner = self.owner_for_constructor(constructor)?;
        let def = self.type_defs.get(&owner)?;
        match &def.kind {
            TypeDefKind::Enum(variants) => variants
                .iter()
                .find(|v| v.name == variant_name)
                .map(|v| v.fields.clone()),
            TypeDefKind::Struct(fields) => Some(fields.iter().map(|f| f.ty.clone()).collect()),
        }
    }

    fn owner_for_constructor(&self, constructor: &str) -> Option<String> {
        let parts: Vec<&str> = constructor
            .split("::")
            .map(str::trim)
            .filter(|p| !p.is_empty())
            .collect();

        if parts.len() >= 2 {
            let owner = parts[parts.len() - 2];
            if self.type_defs.contains_key(owner) {
                return Some(owner.to_string());
            }
        }
        parts
            .last()
            .and_then(|v| self.owner_for_variant_name(v))
    }

    fn owner_for_variant_name(&self, variant_name: &str) -> Option<String> {
        self.variant_owners.get(variant_name).cloned().flatten()
    }

    fn is_copy(&self, ty: &Type, copy_generics: &HashSet<String>) -> bool {
        match ty {
            Type::Named(name) => {
                matches!(
                    name.as_str(),
                    "bool"
                        | "char"
                        | "i8"
                        | "i16"
                        | "i32"
                        | "i64"
                        | "i128"
                        | "isize"
                        | "u8"
                        | "u16"
                        | "u32"
                        | "u64"
                        | "u128"
                        | "usize"
                        | "f32"
                        | "f64"
                ) || self.copy_types.contains(name)
                    || copy_generics.contains(name)
            }
            Type::Generic(name, params) => {
                self.copy_types.contains(name)
                    && params.iter().all(|p| self.is_copy(p, copy_generics))
            }
            Type::Tuple(types) => types.iter().all(|t| self.is_copy(t, copy_generics)),
            Type::Reference(_, _, _) => true, // references are always Copy
            Type::Unit | Type::Never => true,
            _ => false,
        }
    }

    // ── B-Closure ─────────────────────────────────────────────────────────────

    /// Attempt to apply **B-Closure** (paper §4) to the initialiser of a
    /// `let` binding.
    ///
    /// Recognises the Isabelle-generated owncap pattern:
    /// ```text
    /// {
    ///     let y1_cap = y1.clone();
    ///     // …
    ///     (move |x̄| { clo_cap })
    /// }
    /// ```
    /// When *all* `_cap`-captured variables are borrowable within `clo_cap`
    /// (demands ≤ {Obs, Bor, Own}), the whole block is replaced with a plain
    /// non-`move` closure `|x̄| { clo_bor }` where each `yj_cap` is
    /// substituted back to `yj`.
    ///
    /// NonEscAbs is conservatively ensured by the caller: this method is only
    /// used for direct call-local closures or for closure bindings whose later
    /// uses are known not to return, store, pass, or capture the closure.
    fn try_bclosure_rewrite(
        &self,
        init: &Expr,
        orig_env: &TypeEnv,
        copy_generics: &HashSet<String>,
    ) -> Option<Expr> {
        // The owncap block may be wrapped in parentheses.
        let block = match strip_parens(init) {
            Expr::Block(b) => b,
            _ => return None,
        };

        // Collect `(cap_name, orig_name)` pairs from the block's statements.
        // Every statement must be of the form `let NAME_cap = NAME.clone()`.
        let mut captures: Vec<(String, String)> = Vec::new();
        for stmt in &block.stmts {
            if let Statement::Let(ls) = stmt {
                if let Some(init_expr) = &ls.init {
                    if let Expr::MethodCall(recv, method, args) = init_expr {
                        if method == "clone"
                            && args.is_empty()
                            && ls.name.ends_with("_cap")
                        {
                            if let Expr::Ident(orig) = recv.as_ref() {
                                captures.push((ls.name.clone(), orig.clone()));
                                continue;
                            }
                        }
                    }
                }
            }
            // Any non-cap statement → not an owncap block.
            return None;
        }

        // Need at least one captured variable.
        if captures.is_empty() {
            return None;
        }

        // The block's tail expression must be a `move` closure.
        let closure_expr = block.expr.as_deref()?;
        let (params, body) = extract_move_closure_parts(closure_expr)?;

        // Build an env that includes the _cap bindings so that infer_type can
        // resolve their types when checking demands inside the closure body.
        // Each `let y_cap = y.clone()` gives y_cap the same type as y.
        let mut env_with_caps = orig_env.clone();
        for (cap_name, orig_name) in &captures {
            if let Some(ty) = orig_env.get(orig_name) {
                env_with_caps.insert(cap_name.clone(), ty.clone());
            }
        }

        // Check borrowability: for each captured variable (`y_cap`), all
        // demands it generates within the closure body must be ≤ {Obs, Bor, Own}.
        // Use `in_return_ctx = true` because the closure body's tail expression
        // is the closure's return value, so a derived var in tail position is an
        // owned demand that must satisfy OwnOK.
        for (cap_name, _) in &captures {
            let derived: HashSet<String> = [cap_name.clone()].into_iter().collect();
            let mut demands = HashSet::new();
            let mut env_copy = env_with_caps.clone();
            self.collect_demands_expr(
                body,
                &derived,
                &mut env_copy,
                copy_generics,
                &mut demands,
                true, // closure body tail = return context
            );
            if demands.iter().any(|d| is_blocking(*d)) || !own_ok(&demands) {
                return None;
            }
        }

        // All captures are borrowable.  Build substitution: y_cap → y.
        let subst: HashMap<String, String> = captures
            .iter()
            .map(|(cap, orig)| (cap.clone(), orig.clone()))
            .collect();
        let rewritten_body = subst_idents_in_expr(body, &subst);

        // Return a non-move closure — the body now references the outer
        // variables directly and Rust will capture them by shared reference.
        Some(Expr::Closure(
            params.to_vec(),
            Box::new(rewritten_body),
            false,
        ))
    }

}

// ── Pattern utilities ─────────────────────────────────────────────────────────

/// Remove all `box` keywords from a pattern string so it can be used against
/// a `&D<T>` scrutinee.
fn strip_box_from_pattern(pattern: &str) -> String {
    let mut result = String::new();
    let mut remaining = pattern;

    while !remaining.is_empty() {
        if let Some(rest) = remaining.strip_prefix("box ") {
            let rest = rest.trim_start();
            // Take only the identifier characters (stop at punctuation).
            let ident_end = rest
                .find(|c: char| !c.is_ascii_alphanumeric() && c != '_')
                .unwrap_or(rest.len());
            result.push_str(&rest[..ident_end]);
            remaining = &rest[ident_end..];
        } else {
            let next = remaining.find("box ").unwrap_or(remaining.len());
            result.push_str(&remaining[..next]);
            remaining = &remaining[next..];
        }
    }

    result
}

// ── B-Closure helpers ────────────────────────────────────────────────────────

/// Extract the bare parameter name from a possibly-typed closure param string.
/// `"x"` → `"x"`, `"x: Int"` → `"x"`, `"mut x: Int"` → `"x"`.
fn closure_param_name(param_str: &str) -> String {
    param_str
        .trim_start_matches("mut ")
        .split(':')
        .next()
        .unwrap_or(param_str)
        .trim()
        .to_string()
}

#[derive(Debug, Default)]
struct ClosureBindingUsage {
    call_uses: usize,
    escapes: bool,
}

fn closure_binding_is_nonescaping_use(block: &Block, stmt_idx: usize, name: &str) -> bool {
    let mut usage = ClosureBindingUsage::default();
    let mut shadowed = false;

    for stmt in block.stmts.iter().skip(stmt_idx + 1) {
        if shadowed {
            break;
        }
        shadowed = collect_closure_binding_usage_stmt(stmt, name, &mut usage);
        if usage.escapes {
            return false;
        }
    }

    if !shadowed {
        if let Some(tail) = &block.expr {
            collect_closure_binding_usage_expr(tail, name, &mut usage);
        }
    }

    usage.call_uses > 0 && !usage.escapes
}

fn collect_closure_binding_usage_stmt(
    stmt: &Statement,
    name: &str,
    usage: &mut ClosureBindingUsage,
) -> bool {
    match stmt {
        Statement::Let(ls) => {
            if let Some(init) = &ls.init {
                collect_closure_binding_usage_expr(init, name, usage);
            }
            pattern_binds_name(&ls.name, name)
        }
        Statement::Expr(expr) => {
            collect_closure_binding_usage_expr(expr, name, usage);
            false
        }
        Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {
            false
        }
    }
}

fn collect_closure_binding_usage_block(
    block: &Block,
    name: &str,
    usage: &mut ClosureBindingUsage,
) {
    let mut shadowed = false;
    for stmt in &block.stmts {
        if shadowed {
            break;
        }
        shadowed = collect_closure_binding_usage_stmt(stmt, name, usage);
        if usage.escapes {
            return;
        }
    }

    if !shadowed {
        if let Some(tail) = &block.expr {
            collect_closure_binding_usage_expr(tail, name, usage);
        }
    }
}

fn collect_closure_binding_usage_expr(
    expr: &Expr,
    name: &str,
    usage: &mut ClosureBindingUsage,
) {
    if usage.escapes {
        return;
    }

    match expr {
        Expr::Ident(ident) => {
            if ident == name {
                usage.escapes = true;
            }
        }
        Expr::Call(callee, args) => {
            if expr_is_ident_named(callee, name) {
                usage.call_uses += 1;
            } else {
                collect_closure_binding_usage_expr(callee, name, usage);
            }
            for arg in args {
                collect_closure_binding_usage_expr(arg, name, usage);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            collect_closure_binding_usage_expr(receiver, name, usage);
            for arg in args {
                collect_closure_binding_usage_expr(arg, name, usage);
            }
        }
        Expr::Block(block) => {
            collect_closure_binding_usage_block(block, name, usage);
        }
        Expr::Loop(block) | Expr::Unsafe(block) => {
            collect_closure_binding_usage_block(block, name, usage);
        }
        Expr::Await(inner)
        | Expr::Parenthesized(inner)
        | Expr::UnaryOp(_, inner)
        | Expr::Reference(inner, _, _) => {
            collect_closure_binding_usage_expr(inner, name, usage);
        }
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            collect_closure_binding_usage_expr(left, name, usage);
            collect_closure_binding_usage_expr(right, name, usage);
        }
        Expr::Tuple(elems) => {
            for elem in elems {
                collect_closure_binding_usage_expr(elem, name, usage);
            }
        }
        Expr::Match { expr, arms } => {
            collect_closure_binding_usage_expr(expr, name, usage);
            for arm in arms {
                if pattern_binds_name(&arm.pattern, name) {
                    continue;
                }
                if let Some(guard) = &arm.guard {
                    collect_closure_binding_usage_expr(guard, name, usage);
                }
                collect_closure_binding_usage_block(&arm.body, name, usage);
            }
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            collect_closure_binding_usage_expr(condition, name, usage);
            collect_closure_binding_usage_block(then_branch, name, usage);
            if let Some(else_branch) = else_branch {
                collect_closure_binding_usage_block(else_branch, name, usage);
            }
        }
        Expr::IfLet {
            pattern,
            value,
            then_branch,
            else_branch,
        } => {
            collect_closure_binding_usage_expr(value, name, usage);
            if !pattern_binds_name(pattern, name) {
                collect_closure_binding_usage_block(then_branch, name, usage);
            }
            if let Some(else_branch) = else_branch {
                collect_closure_binding_usage_block(else_branch, name, usage);
            }
        }
        Expr::Closure(params, body, _) => {
            if !params.iter().any(|p| closure_param_name(p) == name) {
                let vars = HashSet::from([name.to_string()]);
                if expr_has_free_var_from(body, &vars) {
                    usage.escapes = true;
                }
            }
        }
        Expr::BuilderChain(methods) => {
            let vars = HashSet::from([name.to_string()]);
            if builder_chain_has_free_var_from(methods, &vars) {
                usage.escapes = true;
            }
        }
        Expr::Path(_, _) | Expr::Literal(_) => {}
    }
}

fn expr_is_ident_named(expr: &Expr, name: &str) -> bool {
    matches!(strip_parens(expr), Expr::Ident(ident) if ident == name)
}

/// Returns `true` if any variable in `vars` appears free (not locally bound)
/// anywhere in `expr`.  Conservative over-approximation: does NOT track
/// shadowing from inner `let` bindings or match patterns.
fn expr_has_free_var_from(expr: &Expr, vars: &HashSet<String>) -> bool {
    match expr {
        Expr::Ident(name) => vars.contains(name),
        Expr::Path(_, _) | Expr::Literal(_) => false,
        Expr::MethodCall(recv, _, args) => {
            expr_has_free_var_from(recv, vars)
                || args.iter().any(|a| expr_has_free_var_from(a, vars))
        }
        Expr::Call(callee, args) => {
            expr_has_free_var_from(callee, vars)
                || args.iter().any(|a| expr_has_free_var_from(a, vars))
        }
        Expr::Block(block) => block_has_free_var_from(block, vars),
        Expr::Loop(block) | Expr::Unsafe(block) => block_has_free_var_from(block, vars),
        Expr::Parenthesized(inner)
        | Expr::UnaryOp(_, inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => expr_has_free_var_from(inner, vars),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            expr_has_free_var_from(l, vars) || expr_has_free_var_from(r, vars)
        }
        Expr::Tuple(elems) => elems.iter().any(|e| expr_has_free_var_from(e, vars)),
        Expr::Match { expr, arms } => {
            expr_has_free_var_from(expr, vars)
                || arms
                    .iter()
                    .any(|arm| {
                        arm.guard
                            .as_ref()
                            .map_or(false, |guard| expr_has_free_var_from(guard, vars))
                            || block_has_free_var_from(&arm.body, vars)
                    })
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            expr_has_free_var_from(condition, vars)
                || block_has_free_var_from(then_branch, vars)
                || else_branch
                    .as_ref()
                    .map_or(false, |b| block_has_free_var_from(b, vars))
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            expr_has_free_var_from(value, vars)
                || block_has_free_var_from(then_branch, vars)
                || else_branch
                    .as_ref()
                    .map_or(false, |b| block_has_free_var_from(b, vars))
        }
        Expr::Closure(params, body, _) => {
            // Closure params shadow outer vars.
            let shadowed: HashSet<String> =
                params.iter().map(|p| closure_param_name(p)).collect();
            let outer: HashSet<String> = vars.difference(&shadowed).cloned().collect();
            !outer.is_empty() && expr_has_free_var_from(body, &outer)
        }
        Expr::BuilderChain(methods) => builder_chain_has_free_var_from(methods, vars),
    }
}

fn builder_chain_has_free_var_from(methods: &[BuilderMethod], vars: &HashSet<String>) -> bool {
    methods.iter().any(|method| match method {
        BuilderMethod::Named(_) => false,
        BuilderMethod::Spawn { closure, .. } => expr_has_free_var_from(closure, vars),
    })
}

fn block_has_free_var_from(block: &Block, vars: &HashSet<String>) -> bool {
    // Walk stmts; `let` bindings are NOT subtracted (conservative).
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(ls) => {
                if ls.init.as_ref().map_or(false, |i| expr_has_free_var_from(i, vars)) {
                    return true;
                }
            }
            Statement::Expr(e) => {
                if expr_has_free_var_from(e, vars) {
                    return true;
                }
            }
            _ => {}
        }
    }
    block
        .expr
        .as_ref()
        .map_or(false, |e| expr_has_free_var_from(e, vars))
}

/// Strip parentheses to find the underlying expression.
fn strip_parens(expr: &Expr) -> &Expr {
    match expr {
        Expr::Parenthesized(inner) => strip_parens(inner),
        other => other,
    }
}

/// Extract `(params, body)` from a `move |params| body` closure, handling
/// any number of wrapping parentheses.  Returns `None` for non-move closures.
fn extract_move_closure_parts(expr: &Expr) -> Option<(&[String], &Expr)> {
    match strip_parens(expr) {
        Expr::Closure(params, body, true) => Some((params.as_slice(), body.as_ref())),
        _ => None,
    }
}

/// Walk `expr` and replace every `Ident` whose name is in `subst` with the
/// mapped replacement name.  Respects closure-param shadowing.
fn subst_idents_in_expr(expr: &Expr, subst: &HashMap<String, String>) -> Expr {
    match expr {
        Expr::Ident(name) => {
            if let Some(rep) = subst.get(name) {
                Expr::Ident(rep.clone())
            } else {
                expr.clone()
            }
        }
        Expr::MethodCall(recv, method, args) => Expr::MethodCall(
            Box::new(subst_idents_in_expr(recv, subst)),
            method.clone(),
            args.iter().map(|a| subst_idents_in_expr(a, subst)).collect(),
        ),
        Expr::Call(callee, args) => Expr::Call(
            Box::new(subst_idents_in_expr(callee, subst)),
            args.iter().map(|a| subst_idents_in_expr(a, subst)).collect(),
        ),
        Expr::Block(block) => Expr::Block(subst_idents_in_block(block, subst)),
        Expr::Parenthesized(inner) => {
            Expr::Parenthesized(Box::new(subst_idents_in_expr(inner, subst)))
        }
        Expr::Tuple(elems) => {
            Expr::Tuple(elems.iter().map(|e| subst_idents_in_expr(e, subst)).collect())
        }
        Expr::BinaryOp(l, op, r) => Expr::BinaryOp(
            Box::new(subst_idents_in_expr(l, subst)),
            op.clone(),
            Box::new(subst_idents_in_expr(r, subst)),
        ),
        Expr::UnaryOp(op, inner) => {
            Expr::UnaryOp(op.clone(), Box::new(subst_idents_in_expr(inner, subst)))
        }
        Expr::Reference(inner, a, b) => {
            Expr::Reference(Box::new(subst_idents_in_expr(inner, subst)), *a, *b)
        }
        Expr::Match { expr, arms } => Expr::Match {
            expr: Box::new(subst_idents_in_expr(expr, subst)),
            arms: arms
                .iter()
                .map(|arm| MatchArm {
                    pattern: arm.pattern.clone(),
                    guard: arm.guard.as_ref().map(|g| subst_idents_in_expr(g, subst)),
                    body: subst_idents_in_block(&arm.body, subst),
                })
                .collect(),
        },
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => Expr::If {
            condition: Box::new(subst_idents_in_expr(condition, subst)),
            then_branch: subst_idents_in_block(then_branch, subst),
            else_branch: else_branch
                .as_ref()
                .map(|b| subst_idents_in_block(b, subst)),
        },
        Expr::Closure(params, body, is_move) => {
            // Closure params shadow the substitution.
            let mut inner_subst = subst.clone();
            for p in params {
                inner_subst.remove(&closure_param_name(p));
            }
            Expr::Closure(
                params.clone(),
                Box::new(subst_idents_in_expr(body, &inner_subst)),
                *is_move,
            )
        }
        // All other nodes are leaves or unsupported — return unchanged.
        _ => expr.clone(),
    }
}

fn subst_idents_in_block(block: &Block, subst: &HashMap<String, String>) -> Block {
    let mut inner = subst.clone();
    let mut stmts = Vec::new();
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(ls) => {
                let new_init = ls.init.as_ref().map(|i| subst_idents_in_expr(i, &inner));
                // `let` binding shadows the name for subsequent statements.
                inner.remove(&ls.name);
                stmts.push(Statement::Let(LetStmt {
                    ifmut: ls.ifmut,
                    name: ls.name.clone(),
                    ty: ls.ty.clone(),
                    init: new_init,
                }));
            }
            Statement::Expr(e) => {
                stmts.push(Statement::Expr(subst_idents_in_expr(e, &inner)));
            }
            other => stmts.push(other.clone()),
        }
    }
    Block {
        stmts,
        expr: block
            .expr
            .as_ref()
            .map(|e| Box::new(subst_idents_in_expr(e, &inner))),
    }
}

// ── Stand-alone helpers ───────────────────────────────────────────────────────

fn make_ref_type(ty: &Type) -> Type {
    Type::Reference(Box::new(ty.clone()), true, false)
}

fn is_reference_type(ty: &Type) -> bool {
    matches!(ty, Type::Reference(_, true, _))
}

fn ref_inner(ty: &Type) -> Option<&Type> {
    match ty {
        Type::Reference(inner, true, _) => Some(inner),
        _ => None,
    }
}

fn is_box_type(ty: &Type) -> bool {
    matches!(ty, Type::Generic(name, params) if name == "Box" && params.len() == 1)
}

fn local_type_name(ty: &Type) -> Option<&str> {
    match ty {
        Type::Named(name) => Some(name.as_str()),
        Type::Path(path) => path.last().map(String::as_str),
        Type::Generic(name, _) => Some(name.as_str()),
        _ => None,
    }
}

fn type_substitution(def: &TypeDef, ty: &Type) -> HashMap<String, Type> {
    match ty {
        Type::Generic(_, params) if params.len() == def.generics.len() => def
            .generics
            .iter()
            .cloned()
            .zip(params.iter().cloned())
            .collect(),
        _ => HashMap::new(),
    }
}

fn apply_type_subst(ty: &Type, subst: &HashMap<String, Type>) -> Type {
    match ty {
        Type::Named(name) => subst
            .get(name)
            .cloned()
            .unwrap_or_else(|| Type::Named(name.clone())),
        Type::Generic(name, params) => Type::Generic(
            name.clone(),
            params.iter().map(|p| apply_type_subst(p, subst)).collect(),
        ),
        Type::Tuple(types) => {
            Type::Tuple(types.iter().map(|t| apply_type_subst(t, subst)).collect())
        }
        Type::Array(inner, len) => {
            Type::Array(Box::new(apply_type_subst(inner, subst)), *len)
        }
        Type::Reference(inner, is_ref, mutable) => Type::Reference(
            Box::new(apply_type_subst(inner, subst)),
            *is_ref,
            *mutable,
        ),
        Type::Slice(inner) => Type::Slice(Box::new(apply_type_subst(inner, subst))),
        Type::Path(_) | Type::Unit | Type::Never => ty.clone(),
    }
}

fn callee_fn_name<'a>(callee: &'a Expr) -> Option<&'a str> {
    match callee {
        Expr::Ident(name) => Some(name.as_str()),
        Expr::Path(path, PathType::Namespace) => path.last().map(String::as_str),
        Expr::Parenthesized(inner) => callee_fn_name(inner),
        _ => None,
    }
}

fn function_type_env(f: &FunctionDef) -> TypeEnv {
    f.params
        .iter()
        .filter(|p| !p.name.is_empty())
        .map(|p| (p.name.clone(), p.ty.clone()))
        .collect()
}

fn ensure_function_comment(f: &mut FunctionDef, comment: &str) {
    if !f.docs.iter().any(|doc| doc.trim() == comment) {
        f.docs.push(comment.to_string());
    }
}

fn generic_names_with_bound(f: &FunctionDef, bound: &str) -> HashSet<String> {
    f.generics
        .iter()
        .filter(|g| g.bounds.iter().any(|b| b == bound))
        .map(|g| g.name.clone())
        .collect()
}

// ── String-level pattern utilities (shared with copy_analysis) ────────────────

fn is_binding_ident(input: &str) -> bool {
    let mut chars = input.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    (first == '_' || first.is_ascii_alphabetic())
        && input != "_"
        && !is_reserved_pattern_word(input)
        && chars.all(|ch| ch == '_' || ch.is_ascii_alphanumeric())
}

fn pattern_binds_name(pattern: &str, name: &str) -> bool {
    if !is_binding_ident(name) {
        return false;
    }

    let mut token = String::new();
    for ch in pattern.chars() {
        if ch == '_' || ch.is_ascii_alphanumeric() {
            token.push(ch);
        } else {
            if token == name {
                return true;
            }
            token.clear();
        }
    }

    token == name
}

fn is_reserved_pattern_word(input: &str) -> bool {
    matches!(input, "box" | "false" | "mut" | "ref" | "self" | "true")
}

fn strip_prefix_word<'a>(input: &'a str, word: &str) -> Option<&'a str> {
    let rest = input.strip_prefix(word)?;
    if rest.starts_with(char::is_whitespace) {
        Some(rest.trim_start())
    } else {
        None
    }
}

fn strip_binding_modifiers(mut input: &str) -> &str {
    loop {
        let trimmed = input.trim_start();
        if let Some(rest) = strip_prefix_word(trimmed, "ref") {
            input = rest;
        } else if let Some(rest) = strip_prefix_word(trimmed, "mut") {
            input = rest;
        } else {
            return trimmed;
        }
    }
}

fn outer_parens_inner(input: &str) -> Option<&str> {
    if !input.starts_with('(') || !input.ends_with(')') {
        return None;
    }
    let mut depth = 0usize;
    for (idx, ch) in input.char_indices() {
        match ch {
            '(' => depth += 1,
            ')' => {
                depth = depth.checked_sub(1)?;
                if depth == 0 && idx != input.len() - 1 {
                    return None;
                }
            }
            _ => {}
        }
    }
    if depth == 0 {
        input.strip_prefix('(')?.strip_suffix(')')
    } else {
        None
    }
}

fn split_constructor_pattern(input: &str) -> Option<(&str, Vec<String>)> {
    let mut depth = 0usize;
    let mut start = None;

    for (idx, ch) in input.char_indices() {
        match ch {
            '(' => {
                if depth == 0 {
                    start = Some(idx);
                }
                depth += 1;
            }
            ')' => {
                depth = depth.checked_sub(1)?;
                if depth == 0 && idx != input.len() - 1 {
                    return None;
                }
            }
            _ => {}
        }
    }

    if depth != 0 {
        return None;
    }

    let start = start?;
    let constructor = input[..start].trim();
    if constructor.is_empty() {
        return None;
    }

    let inner = input[start + 1..input.len() - 1].trim();
    Some((constructor, split_top_level_commas(inner)))
}

fn split_top_level_commas(input: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut start = 0usize;
    let mut paren = 0usize;
    let mut bracket = 0usize;
    let mut brace = 0usize;

    for (idx, ch) in input.char_indices() {
        match ch {
            '(' => paren += 1,
            ')' => paren = paren.saturating_sub(1),
            '[' => bracket += 1,
            ']' => bracket = bracket.saturating_sub(1),
            '{' => brace += 1,
            '}' => brace = brace.saturating_sub(1),
            ',' if paren == 0 && bracket == 0 && brace == 0 => {
                parts.push(input[start..idx].trim().to_string());
                start = idx + ch.len_utf8();
            }
            _ => {}
        }
    }
    let last = input[start..].trim();
    if !last.is_empty() {
        parts.push(last.to_string());
    }
    parts
}

#[cfg(test)]
mod tests {
    use super::*;

    fn named(name: &str) -> Type {
        Type::Named(name.to_string())
    }

    fn lit_i(value: i64) -> Expr {
        Expr::Literal(Literal::Int(value))
    }

    fn block_tail(expr: Expr) -> Block {
        Block {
            stmts: vec![],
            expr: Some(Box::new(expr)),
        }
    }

    fn function(name: &str, param_name: &str, param_ty: Type, body: Block) -> FunctionDef {
        FunctionDef {
            name: name.to_string(),
            params: vec![Param {
                name: param_name.to_string(),
                ty: param_ty,
            }],
            return_type: named("bool"),
            generics: vec![],
            body,
            asyncness: false,
            vis: Visibility::Public,
            docs: vec![],
            attrs: vec![],
        }
    }

    fn module_with(function: FunctionDef) -> RustModule {
        RustModule {
            name: "Test".to_string(),
            docs: vec![],
            items: vec![Item::Function(function)],
            attrs: vec![],
            vis: Visibility::Public,
        }
    }

    fn empty_ctx() -> BorrowContext {
        BorrowContext {
            copy_types: HashSet::new(),
            type_defs: HashMap::new(),
            variant_owners: HashMap::new(),
            fn_sigs: HashMap::new(),
            borrow_positions: HashMap::new(),
            borrow_fns: HashSet::new(),
        }
    }

    fn owncap_block(orig_name: &str, cap_name: &str) -> Expr {
        Expr::Block(Block {
            stmts: vec![Statement::Let(LetStmt {
                ifmut: false,
                name: cap_name.to_string(),
                ty: None,
                init: Some(Expr::MethodCall(
                    Box::new(Expr::Ident(orig_name.to_string())),
                    "clone".to_string(),
                    vec![],
                )),
            })],
            expr: Some(Box::new(Expr::Closure(
                vec!["x: i32".to_string()],
                Box::new(Expr::MethodCall(
                    Box::new(Expr::Ident(cap_name.to_string())),
                    "clone".to_string(),
                    vec![],
                )),
                true,
            ))),
        })
    }

    fn block_with_closure_binding(tail: Expr) -> Block {
        Block {
            stmts: vec![Statement::Let(LetStmt {
                ifmut: false,
                name: "f".to_string(),
                ty: None,
                init: Some(owncap_block("y", "y_cap")),
            })],
            expr: Some(Box::new(tail)),
        }
    }

    fn rewrite_test_block(block: &Block) -> Block {
        let ctx = empty_ctx();
        let orig_env = HashMap::from([("y".to_string(), named("String"))]);
        let mut borrow_env = orig_env.clone();
        ctx.rewrite_block_borrow(block, &mut borrow_env, &orig_env, &HashSet::new(), "test")
    }

    fn first_let_init(block: &Block) -> &Expr {
        match &block.stmts[0] {
            Statement::Let(ls) => ls.init.as_ref().expect("let init"),
            _ => panic!("expected let statement"),
        }
    }

    fn is_move_owncap_block(expr: &Expr) -> bool {
        let Expr::Block(block) = strip_parens(expr) else {
            return false;
        };
        matches!(
            block.expr.as_deref().map(strip_parens),
            Some(Expr::Closure(_, _, true))
        )
    }

    #[test]
    fn unk_blocks_borrowing_for_unsupported_index_use() {
        let body = block_tail(Expr::Index(
            Box::new(Expr::Ident("x".to_string())),
            Box::new(lit_i(0)),
        ));
        let mut module = module_with(function("uses_index", "x", named("Tree"), body));

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.is_empty());
        let Item::Function(function) = &module.items[0] else {
            panic!("expected function");
        };
        assert!(!is_reference_type(&function.params[0].ty));
    }

    #[test]
    fn bclosure_rewrites_direct_local_call() {
        let block = block_with_closure_binding(Expr::Call(
            Box::new(Expr::Ident("f".to_string())),
            vec![lit_i(0)],
        ));

        let rewritten = rewrite_test_block(&block);

        assert!(matches!(first_let_init(&rewritten), Expr::Closure(_, _, false)));
    }

    #[test]
    fn bclosure_keeps_move_when_returned_as_component() {
        let block = block_with_closure_binding(Expr::Tuple(vec![
            Expr::Ident("f".to_string()),
            lit_i(0),
        ]));

        let rewritten = rewrite_test_block(&block);

        assert!(is_move_owncap_block(first_let_init(&rewritten)));
    }

    #[test]
    fn bclosure_keeps_move_when_passed_to_unknown_callee() {
        let block = block_with_closure_binding(Expr::Call(
            Box::new(Expr::Ident("consume".to_string())),
            vec![Expr::Ident("f".to_string())],
        ));

        let rewritten = rewrite_test_block(&block);

        assert!(is_move_owncap_block(first_let_init(&rewritten)));
    }

    #[test]
    fn bclosure_keeps_move_when_captured_by_escaping_closure() {
        let block = block_with_closure_binding(Expr::Closure(
            vec![],
            Box::new(Expr::Call(
                Box::new(Expr::Ident("f".to_string())),
                vec![lit_i(0)],
            )),
            false,
        ));

        let rewritten = rewrite_test_block(&block);

        assert!(is_move_owncap_block(first_let_init(&rewritten)));
    }
}
