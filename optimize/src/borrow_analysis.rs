use std::collections::{HashMap, HashSet};

use rustlightast::*;

use crate::rustlight_parser::TYPE_FACT_ONLY_DOC;

use crate::last_use_analysis::{
    rewrite_last_use_clones_in_function, rewrite_last_use_clones_in_owned_expr,
};

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
/// `y_j` gets type `&F_j` (where `F_j` is the j-th field type). A boxed field
/// therefore binds as `&Box<F_inner>` until an explicit `let y = *y_j`
/// extraction is rewritten to `y_j.as_ref()`.
type BorrowEnv = HashMap<String, Type>;

/// Ownership mode of the bindings introduced by one match-pattern component.
///
/// A generated function equation may match all source parameters at once, for
/// example `match (xs, n)`.  Borrow inference is nevertheless decided per
/// parameter, so the corresponding pattern tuple may contain both borrowed and
/// owned components.  Keeping that distinction structurally avoids cloning a
/// borrowed component merely to reconstruct an entirely owned tuple.
#[derive(Debug, Clone)]
enum MatchBindingMode {
    Owned(Type),
    Borrowed(Type),
    Tuple(Vec<MatchBindingMode>),
}

impl MatchBindingMode {
    fn has_borrowed_component(&self) -> bool {
        match self {
            Self::Owned(_) => false,
            Self::Borrowed(_) => true,
            Self::Tuple(modes) => modes.iter().any(Self::has_borrowed_component),
        }
    }

    fn runtime_type(&self) -> Type {
        match self {
            Self::Owned(ty) => ty.clone(),
            Self::Borrowed(inner) => make_ref_type(inner),
            Self::Tuple(modes) => Type::Tuple(modes.iter().map(Self::runtime_type).collect()),
        }
    }
}

#[derive(Debug, Clone)]
struct BorrowedTupleScrutinee {
    expr: Expr,
    binding_mode: MatchBindingMode,
}

/// Canonical package-local function identity: `crate`, zero or more module
/// segments, then the function name.
type FunctionId = Vec<String>;

#[derive(Debug, Clone)]
struct ModuleScope {
    module_path: Vec<String>,
    imports: HashMap<String, Vec<String>>,
    current_function: Option<FunctionId>,
}

#[derive(Debug, Clone)]
struct LocatedFunction {
    id: FunctionId,
    scope: ModuleScope,
    function: FunctionDef,
}

#[derive(Debug, Clone, Copy)]
struct DemandSite<'a> {
    in_return_ctx: bool,
    scope: &'a ModuleScope,
}

impl<'a> DemandSite<'a> {
    fn new(in_return_ctx: bool, scope: &'a ModuleScope) -> Self {
        Self {
            in_return_ctx,
            scope,
        }
    }
}

impl ModuleScope {
    fn resolve_name_path(&self, name: &str) -> Vec<String> {
        if let Some(path) = self.imports.get(name) {
            return path.clone();
        }

        let mut path = self.module_path.clone();
        path.push(name.to_string());
        path
    }

    fn resolve_segments(&self, segments: &[String]) -> Vec<String> {
        let normalized = segments
            .iter()
            .map(|segment| strip_path_segment_generics(segment).to_string())
            .collect::<Vec<_>>();
        let Some((first, rest)) = normalized.split_first() else {
            return Vec::new();
        };

        match first.as_str() {
            "crate" => normalized,
            "self" => {
                let mut path = self.module_path.clone();
                path.extend(rest.iter().cloned());
                path
            }
            "super" => {
                let mut path = self.module_path.clone();
                let mut remaining = normalized.as_slice();
                while matches!(remaining.first().map(String::as_str), Some("super")) {
                    path.pop();
                    remaining = &remaining[1..];
                }
                path.extend(remaining.iter().cloned());
                path
            }
            _ => {
                if let Some(imported) = self.imports.get(first) {
                    let mut path = imported.clone();
                    path.extend(rest.iter().cloned());
                    path
                } else if normalized.len() == 1 {
                    self.resolve_name_path(first)
                } else {
                    let mut path = vec!["crate".to_string()];
                    path.extend(normalized);
                    path
                }
            }
        }
    }
}

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
    /// Scope in which field types were written.  A field such as `Payload`
    /// must keep referring to the declaration module even when the datatype is
    /// matched from a module that defines another `Payload`.
    scope: ModuleScope,
    kind: TypeDefKind,
}

// ── Demand lattice ────────────────────────────────────────────────────────────

/// Ownership demand on a parameter or derived value (paper §4).
///
/// Borrow safety and ownership preference are deliberately separate. `Dup`
/// records an owned value that the original source already materializes by
/// clone/copy, whereas `Move` records a genuine transfer in the analyzed view.
/// The original body and the materialization facts in Γ decide `BorrowSafe`;
/// a Last-Use preview supplies the `Move` provenance used by `PreferOwned`.
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum Demand {
    /// Purely observational (match scrutinee, boolean predicate).
    Obs,
    /// Consumed through a borrowed interface (`&x`, `.as_ref()`).
    Bor,
    /// Local duplication already explicit in the original source.
    Dup(DupUse),
    /// Genuine ownership transfer in the analyzed view.  The accompanying
    /// fact records whether the owned value can be reconstructed locally once
    /// the origin is shared.
    Move(MoveUse, Materialization),
    /// Preference-only marker: several payloads are transferred into one
    /// returned aggregate.  The constituent `Move` demands carry the actual
    /// materialization obligations.
    AggregatePayloadReturn,
    /// Borrow escape – blocks borrow inference.
    Esc,
    /// Unknown or unsupported ownership form.
    Unk,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum DupUse {
    /// Owned value is already produced by an explicit `.clone()` in the source.
    ExplicitClone,
    /// Owned value is obtained by copying a value whose type is known Copy.
    CopyUse,
}

/// Whether the current global context can satisfy a move from a shared origin
/// by copying or cloning the required value locally.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum Materialization {
    Available,
    Unavailable,
}

/// Provenance of a value projected from the parameter under analysis.
///
/// `Structural` denotes the root owner or a field that carries the same
/// recursive datatype family. `Payload` denotes a selected non-recursive
/// field. This distinction lets `PreferOwned` protect reusable structure
/// without suppressing observers such as `nth`, which materialize only one
/// selected element.
#[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
enum Origin {
    Structural,
    Payload,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
enum MoveUse {
    /// The function returns a derived binding directly.
    Return(Origin, String),
    /// A value flows into an aggregate, binding, constructor, or owned callee.
    OwnedSink(Origin, String),
    /// A value is captured by an ownership-taking closure.
    ClosureCapture(Origin, String),
}

/// Variables whose values originate at the parameter currently being
/// analysed. `all` preserves the existing safety taint exactly, while
/// `structural` is the subset relevant to `PreferOwned`.
#[derive(Debug, Clone)]
struct DerivedOrigins {
    all: HashSet<String>,
    structural: HashSet<String>,
    root_family: Option<String>,
}

impl DerivedOrigins {
    fn for_parameter(name: &str, ty: &Type, scope: &ModuleScope) -> Self {
        Self {
            all: [name.to_string()].into_iter().collect(),
            structural: [name.to_string()].into_iter().collect(),
            root_family: outer_nominal_family_in_scope(ty, scope),
        }
    }

    fn contains(&self, name: &str) -> bool {
        self.all.contains(name)
    }

    fn is_empty(&self) -> bool {
        self.all.is_empty()
    }

    fn names(&self) -> &HashSet<String> {
        &self.all
    }

    fn origin(&self, name: &str) -> Option<Origin> {
        self.all.contains(name).then(|| {
            if self.structural.contains(name) {
                Origin::Structural
            } else {
                Origin::Payload
            }
        })
    }

    fn insert(&mut self, name: String, origin: Origin) {
        self.all.insert(name.clone());
        if origin == Origin::Structural {
            self.structural.insert(name);
        } else {
            self.structural.remove(&name);
        }
    }

    fn remove(&mut self, name: &str) {
        self.all.remove(name);
        self.structural.remove(name);
    }

    fn without(&self, names: &HashSet<String>) -> Self {
        let mut result = self.clone();
        for name in names {
            result.remove(name);
        }
        result
    }
}

/// Conservative safety condition used by B-Closure. Its substitution rewriter
/// does not materialize every newly exposed move, so it retains the strict
/// gate. B-Match instead uses `interface_borrow_safe` on occurrence-local
/// demands and materializes supported field moves in its arm rewriter.
fn local_rewrite_safe(demands: &HashSet<Demand>) -> bool {
    demands
        .iter()
        .all(|demand| matches!(demand, Demand::Obs | Demand::Bor | Demand::Dup(_)))
}

/// Semantic/lifetime condition for replacing an owned parameter by a shared
/// one.  A genuine move is safe exactly when the current global context proves
/// that the rewriter can materialize the required owned value locally.
fn interface_borrow_safe(demands: &HashSet<Demand>) -> bool {
    demands.iter().all(|demand| {
        matches!(
            demand,
            Demand::Obs
                | Demand::Bor
                | Demand::Dup(_)
                | Demand::Move(_, Materialization::Available)
                | Demand::AggregatePayloadReturn
        )
    })
}

/// Profitability condition for retaining the original owned interface.
///
/// A last-use move of the root or recursive structure should survive. A
/// selected payload may instead be materialized from a borrow when it only
/// contributes to the result, as in `nth`. Ownership remains preferable when
/// that payload is consumed by another owned operation or is used to rebuild
/// the same nominal datatype family as the input.
fn prefer_owned(demands: &HashSet<Demand>, rebuilds_input_family: bool) -> bool {
    for demand in demands {
        match demand {
            Demand::Move(
                MoveUse::Return(Origin::Structural, _)
                | MoveUse::OwnedSink(Origin::Structural, _)
                | MoveUse::ClosureCapture(Origin::Structural, _),
                _,
            ) => return true,
            Demand::AggregatePayloadReturn => return true,
            Demand::Move(
                MoveUse::OwnedSink(Origin::Payload, _)
                | MoveUse::ClosureCapture(Origin::Payload, _),
                _,
            ) => return true,
            Demand::Move(MoveUse::Return(Origin::Payload, _), _) if rebuilds_input_family => {
                return true;
            }
            _ => {}
        }
    }
    false
}

// ── Main context ──────────────────────────────────────────────────────────────

struct BorrowContext {
    /// Types whose `Copy` implementation was inferred and materialized by the
    /// preceding Copy pass. A `-Copy` ablation supplies an empty set here.
    inferred_copy_types: HashSet<String>,
    /// Types that already carried `#[derive(Copy)]` in the input source. These
    /// facts remain available under `-Copy` because the Copy pass did not
    /// create them.
    source_copy_types: HashSet<String>,
    /// Canonical identities of types with a materialized `Copy`
    /// implementation in the rewritten AST. Only these may license
    /// `*shared` rewrites in emitted Rust.
    materialized_copy_type_ids: HashSet<FunctionId>,
    /// Generic types with an explicit unconditional `impl Copy`, such as the
    /// native `RustWord<W>` adapter whose marker parameter does not constrain
    /// copyability.
    unconditional_copy_types: HashSet<String>,
    materialized_unconditional_copy_type_ids: HashSet<FunctionId>,
    /// Canonical identities of types with a materialized derived Clone
    /// implementation. Generic instances additionally require cloneable
    /// arguments.
    derived_clone_types: HashSet<FunctionId>,
    /// Canonical identities of generic types with an explicit unconditional
    /// `impl Clone`.
    unconditional_clone_types: HashSet<FunctionId>,
    /// Canonical identities of package-local nominal types, used to prevent a
    /// local `Box`, `Rc`, `String`, etc. from inheriting runtime type facts by
    /// name alone.
    local_type_ids: HashSet<FunctionId>,
    /// Package-local datatype definitions keyed by their canonical module path.
    /// Using the full identity keeps same-named datatypes in different modules
    /// distinct throughout field-sensitive borrow analysis.
    type_defs: HashMap<FunctionId, TypeDef>,
    /// Canonical enum-variant identity to canonical owning-datatype identity.
    variant_owners: HashMap<FunctionId, Option<FunctionId>>,
    /// `fully_qualified_fn_id → (generics, param_types, return_type)`
    fn_sigs: HashMap<FunctionId, (Vec<GenericParam>, Vec<Type>, Type)>,
    /// `fully_qualified_fn_id → sorted list of 0-indexed parameter positions that are
    /// borrowable`.  Populated during phase 1.
    borrow_positions: HashMap<FunctionId, Vec<usize>>,
    /// Fully qualified identities of functions whose signatures were rewritten.
    borrow_fns: HashSet<FunctionId>,
}

/// Infer borrowed parameter interfaces for functions in `module`.
///
/// When the Copy pass is enabled, `inferred_copy_types` is its result and lets
/// Borrow use newly materialized Copy facts. A Copy-pass ablation supplies an
/// empty set. Source derives, explicit implementations, and primitive scalar
/// facts are collected independently and remain available under `-Copy`.
pub fn optimize_borrow(
    module: &mut RustModule,
    inferred_copy_types: &HashSet<String>,
) -> BorrowAnalysis {
    let mut modules = [module];
    optimize_borrow_modules(&mut modules, inferred_copy_types)
}

/// Infer borrowed parameter interfaces for every parsed module in a package.
///
/// B-Call consults `Borrow(g)` at call sites, so callee summaries must be
/// computed across module boundaries before any body rewrite starts.
pub fn optimize_borrow_modules(
    modules: &mut [&mut RustModule],
    inferred_copy_types: &HashSet<String>,
) -> BorrowAnalysis {
    let mut located_modules = modules
        .iter_mut()
        .map(|module| {
            (
                vec!["crate".to_string(), module.name.clone()],
                &mut **module,
            )
        })
        .collect::<Vec<_>>();
    optimize_borrow_modules_with_paths(&mut located_modules, inferred_copy_types)
}

/// Package-level borrow inference with canonical module paths supplied by the
/// source-file discovery layer.  This is the entry point used by `cargo-opt`.
pub fn optimize_borrow_modules_with_paths(
    modules: &mut [(Vec<String>, &mut RustModule)],
    inferred_copy_types: &HashSet<String>,
) -> BorrowAnalysis {
    let (mut ctx, functions) = BorrowContext::from_modules(modules, inferred_copy_types);

    // Three-pass design:
    //  1. Analyse every post-copy function, including _copy specialisations.
    //  2. Rewrite selected parameter types in place.
    //  3. Rewrite bodies and direct calls against the final Borrow(g) summaries.
    ctx.analyse_all_functions(&functions);
    for (module_path, module) in modules.iter_mut() {
        ctx.rewrite_all_signatures_in_place(&mut module.items, module_path);
    }
    for (module_path, module) in modules.iter_mut() {
        ctx.rewrite_all_bodies_and_calls_in_place(&mut module.items, module_path);
    }

    BorrowAnalysis {
        borrow_fns: ctx.borrow_fns.into_iter().map(|id| id.join("::")).collect(),
    }
}

// ── BorrowContext construction ────────────────────────────────────────────────

impl BorrowContext {
    fn resolve_callee_id(
        &self,
        callee: &Expr,
        scope: &ModuleScope,
        env: &TypeEnv,
    ) -> Option<FunctionId> {
        let id = match callee {
            Expr::Ident(raw_name) => {
                let name = strip_path_segment_generics(raw_name);
                if env.contains_key(name) {
                    return None;
                }
                scope.resolve_name_path(name)
            }
            Expr::Path(segments, PathType::Namespace) => scope.resolve_segments(segments),
            Expr::Parenthesized(inner) => return self.resolve_callee_id(inner, scope, env),
            _ => return None,
        };

        self.fn_sigs.contains_key(&id).then_some(id)
    }

    /// Positions that accept a shared value at a call site.  This includes
    /// both interfaces inferred by B-Sig and references already declared in
    /// the input; the latter must not be rewritten as ownership-consuming
    /// arguments merely because Borrow did not create them.
    fn callee_borrow_positions(&self, id: &FunctionId) -> Vec<usize> {
        let mut positions = self.borrow_positions.get(id).cloned().unwrap_or_default();
        if let Some((_, params, _)) = self.fn_sigs.get(id) {
            positions.extend(
                params
                    .iter()
                    .enumerate()
                    .filter_map(|(index, ty)| is_reference_type(ty).then_some(index)),
            );
        }
        positions.sort_unstable();
        positions.dedup();
        positions
    }

    fn from_modules(
        modules: &[(Vec<String>, &mut RustModule)],
        inferred_copy_types: &HashSet<String>,
    ) -> (Self, Vec<LocatedFunction>) {
        let mut ctx = Self::empty(inferred_copy_types);
        let mut functions = Vec::new();
        for (module_path, module) in modules {
            ctx.collect_items(&module.items, module_path, &mut functions);
        }
        (ctx, functions)
    }

    fn empty(inferred_copy_types: &HashSet<String>) -> Self {
        Self {
            inferred_copy_types: inferred_copy_types.clone(),
            source_copy_types: HashSet::new(),
            materialized_copy_type_ids: HashSet::new(),
            unconditional_copy_types: HashSet::new(),
            materialized_unconditional_copy_type_ids: HashSet::new(),
            derived_clone_types: HashSet::new(),
            unconditional_clone_types: HashSet::new(),
            local_type_ids: HashSet::new(),
            type_defs: HashMap::new(),
            variant_owners: HashMap::new(),
            fn_sigs: HashMap::new(),
            borrow_positions: HashMap::new(),
            borrow_fns: HashSet::new(),
        }
    }

    fn collect_items(
        &mut self,
        items: &[Item],
        module_path: &[String],
        functions: &mut Vec<LocatedFunction>,
    ) {
        let scope = ModuleScope {
            module_path: module_path.to_vec(),
            imports: collect_imports(items),
            current_function: None,
        };
        for item in items {
            self.collect_item(item, &scope, functions);
        }
    }

    fn collect_item(
        &mut self,
        item: &Item,
        scope: &ModuleScope,
        functions: &mut Vec<LocatedFunction>,
    ) {
        match item {
            Item::Struct(def) => {
                let type_id = scope.resolve_name_path(&def.name);
                self.local_type_ids.insert(type_id.clone());
                if def.derives.iter().any(|derive| derive == "Clone") {
                    self.derived_clone_types.insert(type_id.clone());
                }
                if def.derives.iter().any(|derive| derive == "Copy") {
                    if !self.inferred_copy_types.contains(&def.name) {
                        self.source_copy_types.insert(def.name.clone());
                    }
                    self.materialized_copy_type_ids.insert(type_id.clone());
                }
                self.type_defs.insert(
                    type_id,
                    TypeDef {
                        generics: def.generics.iter().map(|g| g.name.clone()).collect(),
                        scope: scope.clone(),
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
                let type_id = scope.resolve_name_path(&def.name);
                self.local_type_ids.insert(type_id.clone());
                if def.derives.iter().any(|derive| derive == "Clone") {
                    self.derived_clone_types.insert(type_id.clone());
                }
                if def.derives.iter().any(|derive| derive == "Copy") {
                    if !self.inferred_copy_types.contains(&def.name) {
                        self.source_copy_types.insert(def.name.clone());
                    }
                    self.materialized_copy_type_ids.insert(type_id.clone());
                }
                for v in &def.variants {
                    let mut variant_id = type_id.clone();
                    variant_id.push(v.name.clone());
                    self.insert_variant_owner(variant_id, &type_id);
                }
                self.type_defs.insert(
                    type_id,
                    TypeDef {
                        generics: def.generics.iter().map(|g| g.name.clone()).collect(),
                        scope: scope.clone(),
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
                let mut id = scope.module_path.clone();
                id.push(f.name.clone());
                self.fn_sigs.insert(
                    id.clone(),
                    (
                        f.generics.clone(),
                        f.params.iter().map(|p| p.ty.clone()).collect(),
                        f.return_type.clone(),
                    ),
                );
                if !f.docs.iter().any(|doc| doc == TYPE_FACT_ONLY_DOC) {
                    let mut function_scope = scope.clone();
                    function_scope.current_function = Some(id.clone());
                    functions.push(LocatedFunction {
                        id,
                        scope: function_scope,
                        function: f.clone(),
                    });
                }
            }
            Item::Impl(impl_block) => {
                if let (Some(trait_impl), Some(type_id)) = (
                    impl_block.trait_impl.as_ref(),
                    unconditional_impl_target_id(impl_block, scope),
                ) {
                    let name = type_id.last().cloned().unwrap_or_default();
                    if type_is_copy_trait(trait_impl) {
                        self.unconditional_copy_types.insert(name.clone());
                        self.materialized_unconditional_copy_type_ids
                            .insert(type_id.clone());
                    }
                    if type_is_clone_trait(trait_impl) {
                        self.unconditional_clone_types.insert(type_id);
                    }
                }
            }
            Item::Mod(m) => {
                let mut nested_path = scope.module_path.clone();
                nested_path.push(m.name.clone());
                self.collect_items(&m.items, &nested_path, functions);
            }
            _ => {}
        }
    }

    fn insert_variant_owner(&mut self, variant_id: FunctionId, owner_id: &FunctionId) {
        self.variant_owners
            .entry(variant_id)
            .and_modify(|existing| {
                if existing.as_ref() != Some(owner_id) {
                    *existing = None;
                }
            })
            .or_insert_with(|| Some(owner_id.clone()));
    }
}

// ── Phase 1: demand analysis ──────────────────────────────────────────────────

impl BorrowContext {
    /// For every top-level function, determine which parameter positions can be
    /// replaced by shared borrows and record them in `self.borrow_positions`.
    fn analyse_all_functions(&mut self, functions: &[LocatedFunction]) {
        self.borrow_positions.clear();
        for located in functions {
            self.borrow_positions.insert(
                located.id.clone(),
                self.candidate_borrow_positions(&located.function),
            );
        }

        loop {
            let mut changed = false;
            let mut next_positions = HashMap::new();

            for located in functions {
                let previous = self
                    .borrow_positions
                    .get(&located.id)
                    .cloned()
                    .unwrap_or_default();
                let mut positions = self.borrowable_positions(&located.function, &located.scope);
                positions.retain(|position| previous.contains(position));

                if positions != previous {
                    changed = true;
                }
                next_positions.insert(located.id.clone(), positions);
            }

            self.borrow_positions = next_positions;
            if !changed {
                break;
            }
        }

        self.borrow_positions
            .retain(|_, positions| !positions.is_empty());
    }

    fn candidate_borrow_positions(&self, f: &FunctionDef) -> Vec<usize> {
        let copy_generics = generic_names_with_bound(f, "Copy");
        f.params
            .iter()
            .enumerate()
            .filter(|(_, param)| self.is_borrow_candidate_type(&param.ty, &copy_generics))
            .map(|(i, _)| i)
            .collect()
    }

    /// Returns the sorted list of parameter indices that are borrowable for `f`.
    fn borrowable_positions(&self, f: &FunctionDef, scope: &ModuleScope) -> Vec<usize> {
        // BorrowSafe is computed from the original body. PreferOwned consults a
        // separate Last-Use preview so a removable clone is not confused with
        // an intrinsically required move. The actual Last-Use rewrite still
        // runs later in its dedicated pass.
        let mut last_use_view = f.clone();
        rewrite_last_use_clones_in_function(&mut last_use_view);

        let copy_generics = generic_names_with_bound(f, "Copy");
        let base_env = function_type_env(f);

        f.params
            .iter()
            .enumerate()
            .filter(|(_, param)| {
                // Only consider owned (non-reference) parameters.
                self.is_borrow_candidate_type(&param.ty, &copy_generics)
                    && self.is_param_borrowable(
                        f,
                        &last_use_view,
                        param,
                        &base_env,
                        &copy_generics,
                        scope,
                    )
            })
            .map(|(i, _)| i)
            .collect()
    }

    fn is_borrow_candidate_type(&self, ty: &Type, copy_generics: &HashSet<String>) -> bool {
        if is_reference_type(ty) || contains_callable_trait(ty) {
            return false;
        }

        match ty {
            Type::Named(_) | Type::Path(_) | Type::Generic(_, _) => true,
            Type::Tuple(types) => types
                .iter()
                .any(|ty| self.is_borrow_candidate_type(ty, copy_generics)),
            Type::Slice(inner) | Type::Array(inner, _) => {
                self.is_borrow_candidate_type(inner, copy_generics)
            }
            Type::CallableTrait(_) | Type::Reference(_, _, _) | Type::Unit | Type::Never => false,
        }
    }

    /// Checks the final parameter decision:
    ///   Borrowable_Γ(f, x:T) = BorrowSafe_Γ(f, x)
    ///                         ∧ ¬PreferOwnedFlow_Γ(f, x)
    ///                         ∧ ¬PreferByValue_Γ(T)
    fn is_param_borrowable(
        &self,
        f: &FunctionDef,
        last_use_view: &FunctionDef,
        param: &Param,
        base_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> bool {
        let original_demands = self.collect_param_demands(f, param, base_env, copy_generics, scope);
        if !interface_borrow_safe(&original_demands) {
            return false;
        }

        !self.param_prefers_owned(f, last_use_view, param, base_env, copy_generics, scope)
    }

    fn param_prefers_owned(
        &self,
        f: &FunctionDef,
        last_use_view: &FunctionDef,
        param: &Param,
        base_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> bool {
        let preview_demands =
            self.collect_param_demands(last_use_view, param, base_env, copy_generics, scope);
        let rebuilds_input_family =
            same_outer_nominal_family_in_scope(&param.ty, &f.return_type, scope);
        prefer_owned(&preview_demands, rebuilds_input_family)
            || self.prefer_by_value(&param.ty, copy_generics, scope)
    }

    fn collect_param_demands(
        &self,
        f: &FunctionDef,
        param: &Param,
        base_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> HashSet<Demand> {
        let derived = DerivedOrigins::for_parameter(&param.name, &param.ty, scope);

        let mut demands: HashSet<Demand> = HashSet::new();
        let mut env = base_env.clone();

        self.collect_demands_block(
            &f.body,
            &derived,
            &mut env,
            copy_generics,
            &mut demands,
            DemandSite::new(true, scope), // function-body tail is the return value
        );
        demands
    }

    /// Walk a block and collect ownership demands imposed on the derived set.
    fn collect_demands_block(
        &self,
        block: &Block,
        derived: &DerivedOrigins,
        env: &mut TypeEnv,
        copy_generics: &HashSet<String>,
        demands: &mut HashSet<Demand>,
        site: DemandSite<'_>,
    ) {
        let DemandSite {
            in_return_ctx,
            scope,
        } = site;
        let mut local_derived = derived.clone();

        for stmt in &block.stmts {
            match stmt {
                Statement::Let(let_stmt) => {
                    let derived_alias = if let_stmt.ty.is_none() {
                        let_stmt
                            .init
                            .as_ref()
                            .and_then(|init| supported_let_alias_origin(init, &local_derived, env))
                    } else {
                        None
                    };
                    if let Some(init) = &let_stmt.init {
                        let unsupported_borrow_alias = match strip_parens(init) {
                            Expr::MethodCall(_, method, args) => {
                                method == "as_ref" && args.is_empty()
                            }
                            Expr::Reference(_, true, false) => true,
                            _ => false,
                        };
                        if derived_alias.is_none()
                            && unsupported_borrow_alias
                            && derived_borrow_alias_origin(init, &local_derived).is_some()
                        {
                            // The current body rewriter does not maintain a
                            // complete alias type environment for these forms.
                            // Reject the interface rewrite rather than risk a
                            // borrowed temporary or an escaping reference.
                            demands.insert(Demand::Unk);
                        }
                        if derived_alias.is_none() || !is_binding_ident(&let_stmt.name) {
                            // General initializers materialize an owned binding.
                            // Supported untyped aliases are preserved as shared
                            // values; other initializers materialize ownership.
                            self.collect_demands_for_own_arg(
                                init,
                                &local_derived,
                                env,
                                copy_generics,
                                demands,
                                scope,
                            );
                        }
                    }
                    // Update env for subsequent statements.
                    let inferred_ty = let_stmt.ty.clone().or_else(|| {
                        let_stmt
                            .init
                            .as_ref()
                            .and_then(|e| self.infer_type(e, env, scope))
                    });
                    if let Some(ty) = inferred_ty {
                        if is_binding_ident(&let_stmt.name) {
                            // Supported aliases propagate the origin so their
                            // eventual use determines the demand.
                            env.insert(let_stmt.name.clone(), ty);
                        } else {
                            self.bind_pattern_env(&let_stmt.name, &ty, env, scope);
                        }
                    }
                    if is_binding_ident(&let_stmt.name) {
                        local_derived.remove(&let_stmt.name);
                        if let Some(origin) = derived_alias {
                            local_derived.insert(let_stmt.name.clone(), origin);
                        }
                    }
                }
                Statement::Expr(expr) => {
                    self.collect_demands_expr(
                        expr,
                        &local_derived,
                        env,
                        copy_generics,
                        demands,
                        DemandSite::new(false, scope),
                    );
                }
                Statement::Item(_)
                | Statement::Continue
                | Statement::Break
                | Statement::Comment(_) => {}
            }
        }

        if let Some(tail) = &block.expr {
            self.collect_demands_expr(
                tail,
                &local_derived,
                env,
                copy_generics,
                demands,
                DemandSite::new(in_return_ctx, scope),
            );
        }
    }

    /// Walk an expression and collect demands imposed on the derived set.
    fn collect_demands_expr(
        &self,
        expr: &Expr,
        derived: &DerivedOrigins,
        env: &mut TypeEnv,
        copy_generics: &HashSet<String>,
        demands: &mut HashSet<Demand>,
        site: DemandSite<'_>,
    ) {
        let DemandSite {
            in_return_ctx,
            scope,
        } = site;
        match expr {
            // ── Ident: a direct use of a variable ────────────────────────────
            Expr::Ident(name) => {
                if derived.contains(name) {
                    let ty = env.get(name);
                    if in_return_ctx {
                        // Returning a derived value directly.
                        if ty.is_some_and(|ty| self.is_materialized_copy(ty, copy_generics, scope))
                        {
                            // Copy types can be implicitly copied.
                            demands.insert(Demand::Dup(DupUse::CopyUse));
                        } else {
                            // Non-Copy direct return lacks clone/copy evidence.
                            demands.insert(Demand::Move(
                                MoveUse::Return(
                                    derived.origin(name).unwrap_or(Origin::Structural),
                                    name.clone(),
                                ),
                                self.move_materialization(ty, copy_generics, scope),
                            ));
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
                                demands.insert(Demand::Dup(DupUse::ExplicitClone));
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
                            DemandSite::new(false, scope),
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
                            DemandSite::new(false, scope),
                        );
                    }
                    _ => {
                        let uses_derived = expr_has_free_var_from(receiver, derived.names())
                            || args
                                .iter()
                                .any(|arg| expr_has_free_var_from(arg, derived.names()));
                        self.collect_demands_expr(
                            receiver,
                            derived,
                            env,
                            copy_generics,
                            demands,
                            DemandSite::new(false, scope),
                        );
                        for arg in args {
                            self.collect_demands_expr(
                                arg,
                                derived,
                                env,
                                copy_generics,
                                demands,
                                DemandSite::new(false, scope),
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
                self.collect_demands_expr(
                    callee,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );

                let callee_id = self.resolve_callee_id(callee, scope, env);
                let returns_constructor =
                    in_return_ctx && self.is_constructor_callee(callee.as_ref(), scope);
                if returns_constructor
                    && args
                        .iter()
                        .map(|arg| {
                            self.count_direct_payload_returns(
                                arg,
                                derived,
                                env,
                                copy_generics,
                                scope,
                            )
                        })
                        .sum::<usize>()
                        > 1
                {
                    demands.insert(Demand::AggregatePayloadReturn);
                }

                for (j, arg) in args.iter().enumerate() {
                    if returns_constructor {
                        self.collect_demands_for_return_arg(
                            arg,
                            derived,
                            env,
                            copy_generics,
                            demands,
                            scope,
                        );
                        continue;
                    }
                    // Determine whether position j takes an owned or borrowed arg.
                    let borrow_pos = callee_id
                        .as_ref()
                        .is_some_and(|id| self.callee_borrow_positions(id).contains(&j));

                    if borrow_pos {
                        // The callee accepts a shared borrow at this position.
                        // Any use of the derived var here is a Bor demand.
                        self.collect_demands_for_bor_arg(
                            arg,
                            derived,
                            env,
                            copy_generics,
                            demands,
                            scope,
                        );
                    } else {
                        // Owned argument: derived variables must be moved or cloned.
                        self.collect_demands_for_own_arg(
                            arg,
                            derived,
                            env,
                            copy_generics,
                            demands,
                            scope,
                        );
                    }
                }
            }

            // ── Match: match e { arms } ──────────────────────────────────────
            Expr::Match {
                expr: scrutinee,
                arms,
            } => {
                // Isabelle's code generator wraps multi-parameter functions in a
                // tuple match: `match (x, y) { (p1, p2) => body }`.  The tuple
                // construction is an ownership-passing artefact, not a direct
                // ownership demand on the whole tuple:
                // the ownership flows directly into the pattern-bound variables.
                // We detect this case and propagate the derived set through the
                // tuple positions instead of recording a spurious whole-tuple demand.
                let is_tuple_scrutinee = matches!(scrutinee.as_ref(), Expr::Tuple(_));
                let deref_box_scrutinee = deref_ident_name(scrutinee.as_ref()).map(str::to_string);

                if !is_tuple_scrutinee {
                    // The scrutinee is inspected (Obs), not consumed.
                    match scrutinee.as_ref() {
                        Expr::Ident(name) => {
                            if derived.contains(name) {
                                demands.insert(Demand::Obs);
                            }
                        }
                        _ => {
                            if let Some(name) = &deref_box_scrutinee {
                                if derived.contains(name) {
                                    demands.insert(Demand::Obs);
                                }
                            }
                        }
                    }
                    if deref_box_scrutinee.is_none() {
                        self.collect_demands_expr(
                            scrutinee,
                            derived,
                            env,
                            copy_generics,
                            demands,
                            DemandSite::new(false, scope),
                        );
                    }
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
                            self.collect_demands_expr(
                                elem,
                                derived,
                                env,
                                copy_generics,
                                demands,
                                DemandSite::new(false, scope),
                            );
                        }
                    }
                }

                let scrutinee_ty = self.infer_type(scrutinee, env, scope);

                for arm in arms {
                    let mut arm_env = env.clone();
                    let mut arm_derived = derived.clone();

                    if let Some(ty) = &scrutinee_ty {
                        self.bind_pattern_env(&arm.pattern, ty, &mut arm_env, scope);
                        // Variables bound in the pattern are derived if the
                        // scrutinee expression is derived.
                        if let Expr::Ident(sname) = scrutinee.as_ref() {
                            if let Some(origin) = derived.origin(sname) {
                                self.collect_derived_from_pattern(
                                    &arm.pattern,
                                    ty,
                                    origin,
                                    &mut arm_derived,
                                    scope,
                                );
                            }
                        } else if let Some(sname) = &deref_box_scrutinee {
                            if let Some(origin) = derived.origin(sname) {
                                self.collect_derived_from_pattern(
                                    &arm.pattern,
                                    ty,
                                    origin,
                                    &mut arm_derived,
                                    scope,
                                );
                            }
                        } else if is_tuple_scrutinee {
                            self.collect_tuple_derived_from_pattern(
                                scrutinee,
                                &arm.pattern,
                                ty,
                                derived,
                                &mut arm_derived,
                                scope,
                            );
                        }
                    } else if let Some(sname) = &deref_box_scrutinee {
                        if let Some(origin) = derived.origin(sname) {
                            let mut bindings = HashSet::new();
                            collect_deref_box_binding_names_from_body(
                                &arm.pattern,
                                &arm.body,
                                &mut bindings,
                            );
                            for binding in bindings {
                                arm_derived.insert(binding, origin);
                            }
                        }
                    } else if is_tuple_scrutinee {
                        self.collect_untyped_tuple_derived_from_pattern(
                            scrutinee,
                            &arm.pattern,
                            derived,
                            &mut arm_derived,
                        );
                    }

                    if let Some(guard) = &arm.guard {
                        self.collect_demands_expr(
                            guard,
                            &arm_derived,
                            &mut arm_env,
                            copy_generics,
                            demands,
                            DemandSite::new(false, scope),
                        );
                    }
                    self.collect_demands_block(
                        &arm.body,
                        &arm_derived,
                        &mut arm_env,
                        copy_generics,
                        demands,
                        DemandSite::new(in_return_ctx, scope),
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
                self.collect_demands_expr(
                    inner,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );
            }

            // ── &mut: outside the current Isabelle2Rust borrow model ───────────
            Expr::Reference(inner, true, true) => {
                if expr_has_free_var_from(inner, derived.names()) {
                    demands.insert(Demand::Unk);
                }
            }

            // ── Aggregate expressions ────────────────────────────────────────
            Expr::Array(elems) | Expr::Tuple(elems) => {
                if in_return_ctx
                    && elems
                        .iter()
                        .map(|elem| {
                            self.count_direct_payload_returns(
                                elem,
                                derived,
                                env,
                                copy_generics,
                                scope,
                            )
                        })
                        .sum::<usize>()
                        > 1
                {
                    demands.insert(Demand::AggregatePayloadReturn);
                }
                for e in elems {
                    if in_return_ctx {
                        self.collect_demands_for_return_arg(
                            e,
                            derived,
                            env,
                            copy_generics,
                            demands,
                            scope,
                        );
                    } else {
                        // Non-return aggregates materialize an owned local value.
                        self.collect_demands_for_own_arg(
                            e,
                            derived,
                            env,
                            copy_generics,
                            demands,
                            scope,
                        );
                    }
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
                    DemandSite::new(in_return_ctx, scope),
                );
            }

            // ── If / IfLet ───────────────────────────────────────────────────
            Expr::If {
                condition,
                then_branch,
                else_branch,
            } => {
                self.collect_demands_expr(
                    condition,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );
                let mut then_env = env.clone();
                self.collect_demands_block(
                    then_branch,
                    derived,
                    &mut then_env,
                    copy_generics,
                    demands,
                    DemandSite::new(in_return_ctx, scope),
                );
                if let Some(eb) = else_branch {
                    let mut else_env = env.clone();
                    self.collect_demands_block(
                        eb,
                        derived,
                        &mut else_env,
                        copy_generics,
                        demands,
                        DemandSite::new(in_return_ctx, scope),
                    );
                }
            }
            Expr::IfLet {
                pattern,
                value,
                then_branch,
                else_branch,
            } => {
                // Phase 2 does not yet rewrite pattern bindings introduced by
                // `if let` from an inferred shared scrutinee.  Keep such a
                // parameter owned instead of losing projection provenance.
                if expr_has_free_var_from(value, derived.names()) {
                    demands.insert(Demand::Unk);
                }
                self.collect_demands_expr(
                    value,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );
                let mut then_env = env.clone();
                if let Some(ty) = self.infer_type(value, env, scope) {
                    self.bind_pattern_env(pattern, &ty, &mut then_env, scope);
                }
                self.collect_demands_block(
                    then_branch,
                    derived,
                    &mut then_env,
                    copy_generics,
                    demands,
                    DemandSite::new(in_return_ctx, scope),
                );
                if let Some(eb) = else_branch {
                    let mut else_env = env.clone();
                    self.collect_demands_block(
                        eb,
                        derived,
                        &mut else_env,
                        copy_generics,
                        demands,
                        DemandSite::new(in_return_ctx, scope),
                    );
                }
            }

            Expr::Parenthesized(inner) | Expr::Cast(inner, _) => {
                self.collect_demands_expr(
                    inner,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(in_return_ctx, scope),
                );
            }
            Expr::BinaryOp(l, _, r) => {
                self.collect_demands_expr(
                    l,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );
                self.collect_demands_expr(
                    r,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );
            }
            Expr::UnaryOp(_, inner) => {
                self.collect_demands_expr(
                    inner,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );
            }

            // Closure: only generate a demand if a derived variable appears
            // free in the closure body (not shadowed by the closure's own params).
            // For `move` closures the capture is an owned demand; for non-move it
            // is an escaping borrow.
            // The owncap pattern (`let y_cap = y.clone()` + `move |…| {…y_cap…}`)
            // does NOT capture `y` directly — only `y_cap` — so derived vars
            // for `y` don't appear free and no blocking demand is generated.
            Expr::Closure(params, body, is_move) | Expr::TypedClosure(params, _, body, is_move) => {
                let shadowed: HashSet<String> =
                    params.iter().map(|p| closure_param_name(p)).collect();
                let outer_derived = derived.without(&shadowed);
                if !outer_derived.is_empty() && expr_has_free_var_from(body, outer_derived.names())
                {
                    if *is_move {
                        for name in outer_derived.names() {
                            let singleton = [name.clone()].into_iter().collect();
                            if expr_has_free_var_from(body, &singleton) {
                                if env.get(name).is_some_and(|ty| {
                                    self.is_materialized_copy(ty, copy_generics, scope)
                                }) {
                                    demands.insert(Demand::Dup(DupUse::CopyUse));
                                } else {
                                    demands.insert(Demand::Move(
                                        MoveUse::ClosureCapture(
                                            outer_derived
                                                .origin(name)
                                                .unwrap_or(Origin::Structural),
                                            name.clone(),
                                        ),
                                        self.move_materialization(
                                            env.get(name),
                                            copy_generics,
                                            scope,
                                        ),
                                    ));
                                }
                            }
                        }
                    } else {
                        demands.insert(Demand::Esc);
                    }
                }
            }
            Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
            Expr::Loop(block) | Expr::Unsafe(block) => {
                if block_has_free_var_from(block, derived.names()) {
                    demands.insert(Demand::Unk);
                }
            }
            Expr::Await(inner) => {
                if expr_has_free_var_from(inner, derived.names()) {
                    demands.insert(Demand::Unk);
                }
            }
            Expr::BuilderChain(methods) => {
                if builder_chain_has_free_var_from(methods, derived.names()) {
                    demands.insert(Demand::Unk);
                }
            }
            Expr::Index(base, index) | Expr::Assign(base, index) => {
                if expr_has_free_var_from(base, derived.names())
                    || expr_has_free_var_from(index, derived.names())
                {
                    demands.insert(Demand::Unk);
                }
            }
            Expr::Reference(inner, _, _) => {
                if expr_has_free_var_from(inner, derived.names()) {
                    demands.insert(Demand::Unk);
                }
            }
        }
    }

    /// Track a value that contributes directly to the function result.  This
    /// preserves return provenance through tuples and datatype constructors,
    /// while ordinary function calls inside the expression still impose their
    /// own parameter modes.
    fn collect_demands_for_return_arg(
        &self,
        arg: &Expr,
        derived: &DerivedOrigins,
        env: &mut TypeEnv,
        copy_generics: &HashSet<String>,
        demands: &mut HashSet<Demand>,
        scope: &ModuleScope,
    ) {
        self.collect_demands_expr(
            arg,
            derived,
            env,
            copy_generics,
            demands,
            DemandSite::new(true, scope),
        );
    }

    fn count_direct_payload_returns(
        &self,
        expr: &Expr,
        derived: &DerivedOrigins,
        env: &TypeEnv,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> usize {
        match strip_parens(expr) {
            Expr::Ident(name)
                if derived.origin(name) == Some(Origin::Payload)
                    && !env
                        .get(name)
                        .is_some_and(|ty| self.is_materialized_copy(ty, copy_generics, scope)) =>
            {
                1
            }
            Expr::Tuple(elems) | Expr::Array(elems) => elems
                .iter()
                .map(|elem| {
                    self.count_direct_payload_returns(elem, derived, env, copy_generics, scope)
                })
                .sum(),
            Expr::Call(callee, args) if self.is_constructor_callee(callee, scope) => args
                .iter()
                .map(|arg| {
                    self.count_direct_payload_returns(arg, derived, env, copy_generics, scope)
                })
                .sum(),
            Expr::Cast(inner, _) => {
                self.count_direct_payload_returns(inner, derived, env, copy_generics, scope)
            }
            Expr::Block(block) => block.expr.as_deref().map_or(0, |tail| {
                self.count_direct_payload_returns(tail, derived, env, copy_generics, scope)
            }),
            _ => 0,
        }
    }

    fn is_constructor_callee(&self, callee: &Expr, scope: &ModuleScope) -> bool {
        let path = match strip_parens(callee) {
            Expr::Ident(name) => name.clone(),
            Expr::Path(segments, PathType::Namespace) => segments.join("::"),
            _ => return false,
        };
        if self.owner_for_constructor(&path, scope).is_some() {
            return true;
        }

        if matches!(path.as_str(), "Some" | "Ok" | "Err") {
            return true;
        }

        matches!(
            path.as_str(),
            "Box::new"
                | "std::boxed::Box::new"
                | "Rc::new"
                | "std::rc::Rc::new"
                | "Arc::new"
                | "std::sync::Arc::new"
        )
    }

    /// Collect demands for an expression used in an *own* (ownership-consuming)
    /// argument position (e.g., a constructor field or a non-borrow callee).
    fn collect_demands_for_own_arg(
        &self,
        arg: &Expr,
        derived: &DerivedOrigins,
        env: &mut TypeEnv,
        copy_generics: &HashSet<String>,
        demands: &mut HashSet<Demand>,
        scope: &ModuleScope,
    ) {
        match arg {
            Expr::UnaryOp(op, inner) if op == "*" => {
                if let Expr::Ident(name) = inner.as_ref() {
                    if derived.contains(name) {
                        let moved_ty = self.infer_type(arg, env, scope);
                        if moved_ty
                            .as_ref()
                            .is_some_and(|ty| self.is_materialized_copy(ty, copy_generics, scope))
                        {
                            demands.insert(Demand::Dup(DupUse::CopyUse));
                        } else {
                            demands.insert(Demand::Move(
                                MoveUse::OwnedSink(
                                    derived.origin(name).unwrap_or(Origin::Structural),
                                    name.clone(),
                                ),
                                self.move_materialization(moved_ty.as_ref(), copy_generics, scope),
                            ));
                        }
                        return;
                    }
                }
                self.collect_demands_expr(
                    arg,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );
            }
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                if let Expr::Ident(name) = receiver.as_ref() {
                    if derived.contains(name) {
                        // `x.clone()` in own position → Own demand (satisfiable).
                        demands.insert(Demand::Dup(DupUse::ExplicitClone));
                        return;
                    }
                }
                self.collect_demands_expr(
                    arg,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );
            }
            Expr::Ident(name) => {
                if derived.contains(name) {
                    let ty = env.get(name);
                    if ty.is_some_and(|ty| self.is_materialized_copy(ty, copy_generics, scope)) {
                        // Copy type: direct use is an implicit copy – Own demand.
                        demands.insert(Demand::Dup(DupUse::CopyUse));
                    } else {
                        // Non-Copy type passed directly without clone lacks
                        // clone/copy evidence.
                        demands.insert(Demand::Move(
                            MoveUse::OwnedSink(
                                derived.origin(name).unwrap_or(Origin::Structural),
                                name.clone(),
                            ),
                            self.move_materialization(ty, copy_generics, scope),
                        ));
                    }
                } else {
                    self.collect_demands_expr(
                        arg,
                        derived,
                        env,
                        copy_generics,
                        demands,
                        DemandSite::new(false, scope),
                    );
                }
            }
            _ => {
                self.collect_demands_expr(
                    arg,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );
            }
        }
    }

    /// Collect demands for an expression that goes into a *bor*
    /// (shared-borrow) argument position.
    fn collect_demands_for_bor_arg(
        &self,
        arg: &Expr,
        derived: &DerivedOrigins,
        env: &mut TypeEnv,
        copy_generics: &HashSet<String>,
        demands: &mut HashSet<Demand>,
        scope: &ModuleScope,
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
                self.collect_demands_expr(
                    arg,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );
            }
            Expr::Ident(name) if derived.contains(name) => {
                demands.insert(Demand::Bor);
            }
            _ => {
                self.collect_demands_expr(
                    arg,
                    derived,
                    env,
                    copy_generics,
                    demands,
                    DemandSite::new(false, scope),
                );
            }
        }
    }

    /// Extend `derived` with the variables bound by `pattern` matching `ty`.
    fn collect_derived_from_pattern(
        &self,
        pattern: &str,
        ty: &Type,
        source: Origin,
        derived: &mut DerivedOrigins,
        scope: &ModuleScope,
    ) {
        let pattern = pattern.trim();
        if pattern.is_empty() || pattern == "_" || pattern == ".." {
            return;
        }

        let pattern = strip_binding_modifiers(pattern);

        // Tuple pattern: (p1, p2, …)
        if let Some(inner) = outer_parens_inner(pattern) {
            let parts = split_top_level_commas(inner);
            if parts.len() > 1 {
                if let Type::Tuple(types) = ty {
                    for (p, t) in parts.iter().zip(types) {
                        let origin = self.projected_origin(source, t, derived);
                        self.collect_derived_from_pattern(p, t, origin, derived, scope);
                    }
                } else {
                    self.collect_pattern_bindings_with_origin(pattern, source, derived);
                }
                return;
            }
        }

        // Constructor pattern: K(p1, p2, …)
        if let Some((constructor, args)) = split_constructor_pattern(pattern) {
            if let Some(field_types) = self.pattern_field_types(constructor, ty, scope) {
                for (arg, fty) in args.iter().zip(field_types.iter()) {
                    let origin = self.projected_origin(source, fty, derived);
                    self.collect_derived_from_pattern(arg, fty, origin, derived, scope);
                }
            } else {
                self.collect_pattern_bindings_with_origin(pattern, source, derived);
            }
            return;
        }

        if pattern.contains("::") || matches!(pattern, "true" | "false") {
            return;
        }

        if is_binding_ident(pattern) {
            derived.insert(pattern.to_string(), source);
        }
    }

    fn collect_tuple_derived_from_pattern(
        &self,
        scrutinee: &Expr,
        pattern: &str,
        ty: &Type,
        derived: &DerivedOrigins,
        out: &mut DerivedOrigins,
        scope: &ModuleScope,
    ) {
        let (Expr::Tuple(elems), Type::Tuple(types)) = (scrutinee, ty) else {
            return;
        };
        let Some(inner) = outer_parens_inner(pattern.trim()) else {
            return;
        };
        let parts = split_top_level_commas(inner);
        for ((elem, subpattern), field_ty) in elems.iter().zip(parts).zip(types) {
            if let Some(origin) = derived_borrow_alias_origin(elem, derived) {
                self.collect_derived_from_pattern(&subpattern, field_ty, origin, out, scope);
            }
        }
    }

    fn collect_untyped_tuple_derived_from_pattern(
        &self,
        scrutinee: &Expr,
        pattern: &str,
        derived: &DerivedOrigins,
        out: &mut DerivedOrigins,
    ) {
        let Expr::Tuple(elems) = scrutinee else {
            return;
        };
        let Some(inner) = outer_parens_inner(pattern.trim()) else {
            return;
        };
        let parts = split_top_level_commas(inner);
        for (elem, subpattern) in elems.iter().zip(parts) {
            if let Some(origin) = derived_borrow_alias_origin(elem, derived) {
                // Without the field type we cannot safely distinguish a
                // recursive projection from a payload projection.
                self.collect_pattern_bindings_with_origin(&subpattern, origin, out);
            }
        }
    }

    fn collect_pattern_bindings_with_origin(
        &self,
        pattern: &str,
        origin: Origin,
        derived: &mut DerivedOrigins,
    ) {
        let mut bindings = HashSet::new();
        collect_pattern_binding_names(pattern, &mut bindings);
        for binding in bindings {
            derived.insert(binding, origin);
        }
    }

    fn projected_origin(
        &self,
        source: Origin,
        field_ty: &Type,
        derived: &DerivedOrigins,
    ) -> Origin {
        if source == Origin::Payload {
            return Origin::Payload;
        }
        match derived.root_family.as_deref() {
            Some(root_family) if type_carries_nominal_family(field_ty, root_family) => {
                Origin::Structural
            }
            Some(_) => Origin::Payload,
            None => Origin::Payload,
        }
    }
}

// ── Phase 2/3: rewrite signatures and bodies in place ────────────────────────

impl BorrowContext {
    fn rewrite_all_signatures_in_place(&mut self, items: &mut [Item], module_path: &[String]) {
        for item in items {
            match item {
                Item::Function(f) => {
                    let mut id = module_path.to_vec();
                    id.push(f.name.clone());
                    self.rewrite_signature_in_place(f, &id);
                }
                Item::Mod(m) => {
                    let mut nested_path = module_path.to_vec();
                    nested_path.push(m.name.clone());
                    self.rewrite_all_signatures_in_place(&mut m.items, &nested_path);
                }
                _ => {}
            }
        }
    }

    fn rewrite_signature_in_place(&mut self, f: &mut FunctionDef, id: &FunctionId) {
        let Some(positions) = self.borrow_positions.get(id).cloned() else {
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
        self.borrow_fns.insert(id.clone());
    }

    fn rewrite_all_bodies_and_calls_in_place(&self, items: &mut [Item], module_path: &[String]) {
        let scope = ModuleScope {
            module_path: module_path.to_vec(),
            imports: collect_imports(items),
            current_function: None,
        };
        for item in items {
            match item {
                Item::Function(f) => {
                    let mut id = module_path.to_vec();
                    id.push(f.name.clone());
                    self.rewrite_function_body_in_place(f, &id, &scope);
                }
                Item::Impl(impl_block) => {
                    for impl_item in &mut impl_block.items {
                        if let ImplItem::Method(method) = impl_item {
                            self.rewrite_impl_method_body_in_place(method, &scope);
                        }
                    }
                }
                Item::Mod(m) => {
                    let mut nested_path = module_path.to_vec();
                    nested_path.push(m.name.clone());
                    self.rewrite_all_bodies_and_calls_in_place(&mut m.items, &nested_path);
                }
                _ => {}
            }
        }
    }

    fn rewrite_function_body_in_place(
        &self,
        f: &mut FunctionDef,
        id: &FunctionId,
        scope: &ModuleScope,
    ) {
        let mut borrow_env = function_type_env(f);
        let orig_env = self.original_function_type_env(f, id);
        let copy_generics = generic_names_with_bound(f, "Copy");
        let mut function_scope = scope.clone();
        function_scope.current_function = Some(id.clone());
        f.body = self.rewrite_block_borrow_at(
            &f.body,
            &mut borrow_env,
            &orig_env,
            &copy_generics,
            &function_scope,
            true,
        );
    }

    fn rewrite_impl_method_body_in_place(&self, method: &mut FunctionDef, scope: &ModuleScope) {
        let mut borrow_env = function_type_env(method);
        let orig_env = borrow_env.clone();
        let copy_generics = generic_names_with_bound(method, "Copy");
        method.body = self.rewrite_block_borrow_at(
            &method.body,
            &mut borrow_env,
            &orig_env,
            &copy_generics,
            scope,
            true,
        );
    }

    fn original_function_type_env(&self, f: &FunctionDef, id: &FunctionId) -> TypeEnv {
        let Some((_, param_types, _)) = self.fn_sigs.get(id) else {
            return function_type_env(f);
        };

        f.params
            .iter()
            .zip(param_types.iter())
            .filter(|(param, _)| !param.name.is_empty())
            .map(|(param, ty)| (param.name.clone(), ty.clone()))
            .collect()
    }

    /// Decide the second case of R-Match for one owned scrutinee occurrence.
    ///
    /// Safety is computed from the original match after normalizing either
    /// `match x` or `match x.clone()` to the same provenance root. Profitability
    /// is computed from an analysis-only Last-Use view of this occurrence, so
    /// removable field clones remain visible as ownership moves to
    /// `PreferOwned`. No function-level parameter flag is reused here: two
    /// matches over the same owner may make different decisions.
    fn local_match_borrowable(
        &self,
        match_expr: &Expr,
        root: &str,
        orig_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
        in_return_ctx: bool,
    ) -> bool {
        let Some(root_ty) = orig_env.get(root) else {
            return false;
        };
        if is_reference_type(root_ty)
            || (self.is_materialized_copy(root_ty, copy_generics, scope)
                && self.prefer_copy_match_by_value(root_ty, copy_generics, scope))
        {
            return false;
        }

        let Some(original_view) = normalize_match_scrutinee(match_expr, root) else {
            return false;
        };
        let derived = DerivedOrigins::for_parameter(root, root_ty, scope);
        let mut original_demands = HashSet::new();
        let mut original_env = orig_env.clone();
        self.collect_demands_expr(
            &original_view,
            &derived,
            &mut original_env,
            copy_generics,
            &mut original_demands,
            DemandSite::new(in_return_ctx, scope),
        );
        if !interface_borrow_safe(&original_demands) {
            return false;
        }

        let mut last_use_view = match_expr.clone();
        let owned = [root.to_string()].into_iter().collect();
        rewrite_last_use_clones_in_owned_expr(&mut last_use_view, &owned);
        let Some(last_use_view) = normalize_match_scrutinee(&last_use_view, root) else {
            return false;
        };
        let mut preview_demands = HashSet::new();
        let mut preview_env = orig_env.clone();
        self.collect_demands_expr(
            &last_use_view,
            &derived,
            &mut preview_env,
            copy_generics,
            &mut preview_demands,
            DemandSite::new(in_return_ctx, scope),
        );

        let function_rebuilds_root = in_return_ctx
            && scope
                .current_function
                .as_ref()
                .and_then(|id| self.fn_sigs.get(id))
                .is_some_and(|(_, _, return_ty)| {
                    same_outer_nominal_family_in_scope(root_ty, return_ty, scope)
                });
        let match_rebuilds_root = self
            .infer_type(&last_use_view, orig_env, scope)
            .is_some_and(|result_ty| {
                same_outer_nominal_family_in_scope(root_ty, &result_ty, scope)
            });

        !prefer_owned(
            &preview_demands,
            function_rebuilds_root || match_rebuilds_root,
        )
    }

    /// Rewrite a generated tuple-match scrutinee component by component.
    ///
    /// Function equations preserve their complete source parameter vector as
    /// one Rust tuple match.  B-Sig may still borrow only a subset of those
    /// parameters.  The returned mode tree records that subset without
    /// deleting or rearranging any tuple component or materializing a borrowed
    /// recursive value with `.clone()`.
    fn rewrite_borrowed_tuple_scrutinee(
        &self,
        scrutinee: &Expr,
        borrow_env: &BorrowEnv,
        orig_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> Option<BorrowedTupleScrutinee> {
        let Expr::Tuple(elems) = scrutinee else {
            return None;
        };

        let mut rewritten = Vec::with_capacity(elems.len());
        let mut modes = Vec::with_capacity(elems.len());
        for elem in elems {
            let (new_elem, mode) = self.rewrite_tuple_match_component(
                elem,
                borrow_env,
                orig_env,
                copy_generics,
                scope,
            )?;
            rewritten.push(new_elem);
            modes.push(mode);
        }

        let binding_mode = MatchBindingMode::Tuple(modes);
        binding_mode
            .has_borrowed_component()
            .then_some(BorrowedTupleScrutinee {
                expr: Expr::Tuple(rewritten),
                binding_mode,
            })
    }

    fn rewrite_tuple_match_component(
        &self,
        expr: &Expr,
        borrow_env: &BorrowEnv,
        orig_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> Option<(Expr, MatchBindingMode)> {
        if let Some((borrowed_expr, borrow_ty)) = borrowed_local_alias(expr, borrow_env) {
            let inner_ty = ref_inner(&borrow_ty)?.clone();
            return Some((borrowed_expr, MatchBindingMode::Borrowed(inner_ty)));
        }

        if let Expr::Tuple(elems) = strip_parens(expr) {
            let mut rewritten = Vec::with_capacity(elems.len());
            let mut modes = Vec::with_capacity(elems.len());
            for elem in elems {
                let (new_elem, mode) = self.rewrite_tuple_match_component(
                    elem,
                    borrow_env,
                    orig_env,
                    copy_generics,
                    scope,
                )?;
                rewritten.push(new_elem);
                modes.push(mode);
            }
            return Some((Expr::Tuple(rewritten), MatchBindingMode::Tuple(modes)));
        }

        let ty = self.infer_type(expr, orig_env, scope)?;
        Some((
            self.rewrite_expr_own(expr, borrow_env, orig_env, copy_generics, scope),
            MatchBindingMode::Owned(ty),
        ))
    }

    // ── Body rewriter ─────────────────────────────────────────────────────────

    #[cfg(test)]
    fn rewrite_block_borrow(
        &self,
        block: &Block,
        borrow_env: &mut BorrowEnv,
        orig_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> Block {
        self.rewrite_block_borrow_at(block, borrow_env, orig_env, copy_generics, scope, false)
    }

    fn rewrite_block_borrow_at(
        &self,
        block: &Block,
        borrow_env: &mut BorrowEnv,
        orig_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
        in_return_ctx: bool,
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
                            self.try_bclosure_rewrite(init, &local_orig, copy_generics, scope)
                        })
                    } else {
                        None
                    };
                    let borrowed_alias = if bclosure.is_none()
                        && let_stmt.ty.is_none()
                        && is_binding_ident(&let_stmt.name)
                        // Generated `_cap` bindings feed `move` closures that
                        // may escape the current function.  Keep the capture
                        // value owned; otherwise a borrowed pattern field can
                        // be stored in the required `'static` closure object.
                        && !let_stmt.name.ends_with("_cap")
                    {
                        let_stmt
                            .init
                            .as_ref()
                            .and_then(|init| borrowed_local_alias(init, borrow_env))
                    } else {
                        None
                    };
                    let new_init = if let Some(closure_expr) = bclosure {
                        Some(closure_expr)
                    } else if let Some((alias_expr, _)) = &borrowed_alias {
                        Some(alias_expr.clone())
                    } else {
                        let_stmt.init.as_ref().map(|init| {
                            self.rewrite_expr_own(
                                init,
                                borrow_env,
                                &local_orig,
                                copy_generics,
                                scope,
                            )
                        })
                    };
                    // Update environments.
                    if let Some(ty) = let_stmt.ty.clone().or_else(|| {
                        let_stmt
                            .init
                            .as_ref()
                            .and_then(|e| self.infer_type(e, &local_orig, scope))
                    }) {
                        if is_binding_ident(&let_stmt.name) {
                            local_orig.insert(let_stmt.name.clone(), ty.clone());
                            if let Some((_, borrow_ty)) = &borrowed_alias {
                                borrow_env.insert(let_stmt.name.clone(), borrow_ty.clone());
                            } else {
                                borrow_env.insert(let_stmt.name.clone(), ty);
                            }
                        } else {
                            self.bind_pattern_env(&let_stmt.name, &ty, &mut local_orig, scope);
                            self.bind_pattern_env_for_borrow(
                                &let_stmt.name,
                                &ty,
                                borrow_env,
                                scope,
                            );
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
                        scope,
                    )));
                }
                Statement::Item(item) => stmts.push(Statement::Item(item.clone())),
                Statement::Continue => stmts.push(Statement::Continue),
                Statement::Break => stmts.push(Statement::Break),
                Statement::Comment(c) => stmts.push(Statement::Comment(c.clone())),
            }
        }

        let tail = block.expr.as_ref().map(|e| {
            Box::new(self.rewrite_expr_own_at(
                e,
                borrow_env,
                &local_orig,
                copy_generics,
                scope,
                in_return_ctx,
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
        scope: &ModuleScope,
    ) -> Expr {
        self.rewrite_expr_own_at(expr, borrow_env, orig_env, copy_generics, scope, false)
    }

    fn rewrite_expr_own_at(
        &self,
        expr: &Expr,
        borrow_env: &BorrowEnv,
        orig_env: &TypeEnv,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
        in_return_ctx: bool,
    ) -> Expr {
        match expr {
            // ── Direct use of a borrowed variable in own context ──────────────
            Expr::Ident(name) => {
                if let Some(bty) = borrow_env.get(name) {
                    if is_reference_type(bty) {
                        // A reference already present in the input is itself
                        // the value of this expression.  Cloning the pointee is
                        // only necessary when B-Sig changed an owned `T` into
                        // `&T`.
                        if orig_env.get(name).is_some_and(is_reference_type) {
                            return expr.clone();
                        }
                        // &T in own context: deref-copy if Copy, else clone.
                        let inner = ref_inner(bty);
                        if self.is_materialized_copy(inner.unwrap_or(bty), copy_generics, scope) {
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
                            return if self.is_materialized_copy(
                                inner.unwrap_or(bty),
                                copy_generics,
                                scope,
                            ) {
                                // Method resolution on `v: &T` may select
                                // `Clone for T` and produce an owned `T`.  Once
                                // the preceding Copy analysis has proved `T:
                                // Copy`, preserve that result without retaining
                                // a redundant clone introduced by B-Match.
                                Expr::UnaryOp("*".to_string(), Box::new(Expr::Ident(name.clone())))
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
                        receiver,
                        borrow_env,
                        orig_env,
                        copy_generics,
                        scope,
                    )),
                    method.clone(),
                    args.iter()
                        .map(|a| {
                            self.rewrite_expr_own(a, borrow_env, orig_env, copy_generics, scope)
                        })
                        .collect(),
                )
            }

            // ── Call: adapt arguments to the callee's final parameter mode ────
            Expr::Call(callee, args) => {
                let callee_id = self.resolve_callee_id(callee, scope, orig_env);

                let borrow_positions = callee_id
                    .as_ref()
                    .map(|id| self.callee_borrow_positions(id))
                    .unwrap_or_default();
                if !borrow_positions.is_empty() {
                    let new_callee = callee.as_ref().clone();
                    let new_args: Vec<Expr> = args
                        .iter()
                        .enumerate()
                        .map(|(j, arg)| {
                            if borrow_positions.contains(&j) {
                                // B-Call bor position: prepare a shared argument.
                                self.bor_transform(arg, borrow_env, orig_env, copy_generics, scope)
                            } else {
                                // Own position: preserve owned semantics.
                                self.rewrite_expr_own(
                                    arg,
                                    borrow_env,
                                    orig_env,
                                    copy_generics,
                                    scope,
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
                    .try_bclosure_rewrite(callee, orig_env, copy_generics, scope)
                    .unwrap_or_else(|| {
                        self.rewrite_expr_own(callee, borrow_env, orig_env, copy_generics, scope)
                    });
                let returns_constructor =
                    in_return_ctx && self.is_constructor_callee(callee.as_ref(), scope);
                let new_args = args
                    .iter()
                    .map(|a| {
                        self.rewrite_expr_own_at(
                            a,
                            borrow_env,
                            orig_env,
                            copy_generics,
                            scope,
                            returns_constructor,
                        )
                    })
                    .collect();
                Expr::Call(Box::new(new_callee), new_args)
            }

            // ── Match: B-Match rule ───────────────────────────────────────────
            Expr::Match {
                expr: scrutinee,
                arms,
            } => {
                // For a borrowed scrutinee keep it as-is: Rust match ergonomics
                // handles matching on `&T` with plain `T` patterns.  Calling
                // rewrite_expr_own would wrongly insert a `.clone()`.
                let deref_borrowed_box_scrutinee =
                    deref_ident_name(scrutinee.as_ref()).and_then(|name| {
                        borrow_env
                            .get(name)
                            .and_then(borrowed_box_inner_type)
                            .map(|inner| (name.to_string(), inner.clone()))
                    });
                let borrowed_tuple_scrutinee = self.rewrite_borrowed_tuple_scrutinee(
                    scrutinee.as_ref(),
                    borrow_env,
                    orig_env,
                    copy_generics,
                    scope,
                );
                // A clone-marked match can still arise for a non-Copy type or
                // when Copy is disabled. Apply the same occurrence-local rule
                // used for a direct `match x` below.
                let clone_match = match scrutinee.as_ref() {
                    Expr::MethodCall(receiver, method, args)
                        if method == "clone" && args.is_empty() =>
                    {
                        if let Expr::Ident(name) = receiver.as_ref() {
                            let receiver_is_borrowed =
                                borrow_env.get(name).is_some_and(is_reference_type);
                            self.infer_type(receiver, orig_env, scope).and_then(|ty| {
                                self.type_def_for_type(&ty, scope).is_some().then(|| {
                                    let materialize_by_value =
                                        self.is_materialized_copy(&ty, copy_generics, scope)
                                            && self.prefer_copy_match_by_value(
                                                &ty,
                                                copy_generics,
                                                scope,
                                            );
                                    let preserve_owned_clone = !receiver_is_borrowed
                                        && !materialize_by_value
                                        && !self.local_match_borrowable(
                                            expr,
                                            name,
                                            orig_env,
                                            copy_generics,
                                            scope,
                                            in_return_ctx,
                                        );
                                    (
                                        receiver.as_ref().clone(),
                                        ty,
                                        receiver_is_borrowed,
                                        materialize_by_value,
                                        preserve_owned_clone,
                                    )
                                })
                            })
                        } else {
                            None
                        }
                    }
                    _ => None,
                };
                let local_direct_match = match scrutinee.as_ref() {
                    Expr::Ident(name) if !borrow_env.get(name).is_some_and(is_reference_type) => {
                        orig_env.get(name).and_then(|ty| {
                            (!is_reference_type(ty)
                                && self.type_def_for_type(ty, scope).is_some()
                                && self.local_match_borrowable(
                                    expr,
                                    name,
                                    orig_env,
                                    copy_generics,
                                    scope,
                                    in_return_ctx,
                                ))
                            .then(|| ty.clone())
                        })
                    }
                    _ => None,
                };
                let borrow_match_inner_type = match scrutinee.as_ref() {
                    Expr::Ident(name) => borrow_env
                        .get(name)
                        .filter(|ty| is_reference_type(ty))
                        .and_then(ref_inner)
                        .cloned()
                        .or_else(|| local_direct_match.clone()),
                    _ => deref_borrowed_box_scrutinee
                        .as_ref()
                        .map(|(_, inner)| inner.clone())
                        .or_else(|| {
                            clone_match.as_ref().and_then(
                                |(_, ty, _, materialize_by_value, preserve_owned_clone)| {
                                    (!materialize_by_value && !preserve_owned_clone)
                                        .then(|| ty.clone())
                                },
                            )
                        }),
                };
                // Copy runs before Borrow and can turn `match x.clone()` into
                // direct `match x` while `x` is still owned. After B-Sig
                // changes `x` to `&T`, blindly retaining that scrutinee would
                // switch a small by-value match into a reference match.
                // Preserve the by-value shape for Copy values of at most two
                // machine words, and reserve field-sensitive borrowing for
                // larger outer objects.
                let materialize_direct_small_copy_match =
                    matches!(
                        scrutinee.as_ref(),
                        Expr::Ident(name)
                            if orig_env.get(name).is_some_and(|ty| !is_reference_type(ty))
                    ) && borrow_match_inner_type.as_ref().is_some_and(|ty| {
                        self.is_materialized_copy(ty, copy_generics, scope)
                            && self.prefer_copy_match_by_value(ty, copy_generics, scope)
                    });
                let materialize_clone_match = clone_match
                    .as_ref()
                    .is_some_and(|(_, _, _, materialize_by_value, _)| *materialize_by_value);
                let scrutinee_is_borrowed = (borrow_match_inner_type.is_some()
                    || borrowed_tuple_scrutinee.is_some())
                    && !materialize_direct_small_copy_match;

                let new_scrutinee = if clone_match
                    .as_ref()
                    .is_some_and(|(_, _, _, _, preserve_owned_clone)| *preserve_owned_clone)
                {
                    // PreferOwned protects the original ownership path. Keep
                    // the clone until the dedicated Last-Use pass proves that
                    // this occurrence can become a move.
                    self.rewrite_expr_own(scrutinee, borrow_env, orig_env, copy_generics, scope)
                } else if let Some((receiver, _, receiver_is_borrowed, _, _)) =
                    clone_match.as_ref().filter(|_| materialize_clone_match)
                {
                    if *receiver_is_borrowed {
                        Expr::UnaryOp("*".to_string(), Box::new(receiver.clone()))
                    } else {
                        receiver.clone()
                    }
                } else if let Some((receiver, _, receiver_is_borrowed, _, _)) = &clone_match {
                    if *receiver_is_borrowed {
                        receiver.clone()
                    } else {
                        Expr::Reference(Box::new(receiver.clone()), true, false)
                    }
                } else if materialize_direct_small_copy_match {
                    Expr::UnaryOp("*".to_string(), Box::new(scrutinee.as_ref().clone()))
                } else if let Some((name, _)) = &deref_borrowed_box_scrutinee {
                    borrowed_box_as_ref(name)
                } else if let Some(tuple) = &borrowed_tuple_scrutinee {
                    tuple.expr.clone()
                } else if local_direct_match.is_some() {
                    Expr::Reference(Box::new(scrutinee.as_ref().clone()), true, false)
                } else if scrutinee_is_borrowed {
                    scrutinee.as_ref().clone()
                } else {
                    self.rewrite_expr_own(scrutinee, borrow_env, orig_env, copy_generics, scope)
                };

                let new_arms: Vec<MatchArm> = arms
                    .iter()
                    .map(|arm| {
                        let mut arm_borrow = borrow_env.clone();
                        let mut arm_orig = orig_env.clone();
                        let new_pattern;

                        if let Some(tuple) = &borrowed_tuple_scrutinee {
                            // A generated tuple match preserves the complete
                            // source parameter vector.  Bind each component in
                            // its independently inferred ownership mode.
                            self.bind_pattern_env_for_match_mode(
                                &arm.pattern,
                                &tuple.binding_mode,
                                &mut arm_borrow,
                                scope,
                            );
                            if let Some(ty) = self.infer_type(scrutinee, orig_env, scope) {
                                self.bind_pattern_env(&arm.pattern, &ty, &mut arm_orig, scope);
                            }
                            mark_deref_box_bindings_from_body(
                                &arm.pattern,
                                &arm.body,
                                &mut arm_borrow,
                            );
                            new_pattern = arm.pattern.clone();
                        } else if scrutinee_is_borrowed {
                            // B-Match keeps the stable pattern unchanged; field
                            // variables get type `&F_j` (a reference to the
                            // original field type).
                            let inner_ty = borrow_match_inner_type.as_ref().unwrap();

                            // Compute field types for this constructor from the
                            // inner (non-reference) scrutinee type.
                            self.bind_pattern_env_for_borrow_match(
                                &arm.pattern,
                                inner_ty,
                                &mut arm_borrow,
                                scope,
                            );
                            self.bind_pattern_env(&arm.pattern, inner_ty, &mut arm_orig, scope);
                            mark_deref_box_bindings_from_body(
                                &arm.pattern,
                                &arm.body,
                                &mut arm_borrow,
                            );
                            new_pattern = arm.pattern.clone();
                        } else {
                            // Non-borrowed scrutinee: pattern unchanged.
                            if let Some(ty) = self.infer_type(scrutinee, orig_env, scope) {
                                self.bind_pattern_env(&arm.pattern, &ty, &mut arm_orig, scope);
                                self.bind_pattern_env_for_borrow(
                                    &arm.pattern,
                                    &ty,
                                    &mut arm_borrow,
                                    scope,
                                );
                            }
                            new_pattern = arm.pattern.clone();
                        }

                        let new_guard = arm.guard.as_ref().map(|g| {
                            self.rewrite_expr_own(g, &arm_borrow, &arm_orig, copy_generics, scope)
                        });
                        let new_body = self.rewrite_block_borrow_at(
                            &arm.body,
                            &mut arm_borrow,
                            &arm_orig,
                            copy_generics,
                            scope,
                            in_return_ctx,
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
                Expr::Block(self.rewrite_block_borrow_at(
                    block,
                    &mut inner_borrow,
                    orig_env,
                    copy_generics,
                    scope,
                    in_return_ctx,
                ))
            }

            // ── Aggregate expressions ─────────────────────────────────────────
            Expr::Array(elems) => Expr::Array(
                elems
                    .iter()
                    .map(|e| {
                        self.rewrite_expr_own_at(
                            e,
                            borrow_env,
                            orig_env,
                            copy_generics,
                            scope,
                            in_return_ctx,
                        )
                    })
                    .collect(),
            ),
            Expr::Tuple(elems) => Expr::Tuple(
                elems
                    .iter()
                    .map(|e| {
                        self.rewrite_expr_own_at(
                            e,
                            borrow_env,
                            orig_env,
                            copy_generics,
                            scope,
                            in_return_ctx,
                        )
                    })
                    .collect(),
            ),

            // ── Reference ────────────────────────────────────────────────────
            Expr::Reference(inner, is_ref, is_mut) => {
                // If B-Sig has already changed `x: T` into `x: &T`, an
                // original `&x` is now a redundant reborrow.  Rewriting the
                // inner expression as owned would instead create
                // `&x.clone()`, whose temporary cannot back a shared tail.
                if *is_ref && !*is_mut {
                    if let Expr::Ident(name) = inner.as_ref() {
                        if borrow_env.get(name).is_some_and(is_reference_type) {
                            return Expr::Ident(name.clone());
                        }
                    }
                }
                Expr::Reference(
                    Box::new(self.rewrite_expr_own(
                        inner,
                        borrow_env,
                        orig_env,
                        copy_generics,
                        scope,
                    )),
                    *is_ref,
                    *is_mut,
                )
            }

            // ── If ────────────────────────────────────────────────────────────
            Expr::If {
                condition,
                then_branch,
                else_branch,
            } => {
                let new_cond =
                    self.rewrite_expr_own(condition, borrow_env, orig_env, copy_generics, scope);
                let mut then_borrow = borrow_env.clone();
                let new_then = self.rewrite_block_borrow_at(
                    then_branch,
                    &mut then_borrow,
                    orig_env,
                    copy_generics,
                    scope,
                    in_return_ctx,
                );
                let new_else = else_branch.as_ref().map(|eb| {
                    let mut else_borrow = borrow_env.clone();
                    self.rewrite_block_borrow_at(
                        eb,
                        &mut else_borrow,
                        orig_env,
                        copy_generics,
                        scope,
                        in_return_ctx,
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
                let new_value =
                    self.rewrite_expr_own(value, borrow_env, orig_env, copy_generics, scope);
                let mut then_borrow = borrow_env.clone();
                let new_then = self.rewrite_block_borrow_at(
                    then_branch,
                    &mut then_borrow,
                    orig_env,
                    copy_generics,
                    scope,
                    in_return_ctx,
                );
                let new_else = else_branch.as_ref().map(|eb| {
                    let mut else_borrow = borrow_env.clone();
                    self.rewrite_block_borrow_at(
                        eb,
                        &mut else_borrow,
                        orig_env,
                        copy_generics,
                        scope,
                        in_return_ctx,
                    )
                });
                Expr::IfLet {
                    pattern: pattern.clone(),
                    value: Box::new(new_value),
                    then_branch: new_then,
                    else_branch: new_else,
                }
            }

            Expr::Parenthesized(inner) => Expr::Parenthesized(Box::new(self.rewrite_expr_own_at(
                inner,
                borrow_env,
                orig_env,
                copy_generics,
                scope,
                in_return_ctx,
            ))),
            Expr::Cast(inner, ty) => Expr::Cast(
                Box::new(self.rewrite_expr_own_at(
                    inner,
                    borrow_env,
                    orig_env,
                    copy_generics,
                    scope,
                    in_return_ctx,
                )),
                ty.clone(),
            ),
            Expr::BinaryOp(l, op, r) => Expr::BinaryOp(
                Box::new(self.rewrite_expr_own(l, borrow_env, orig_env, copy_generics, scope)),
                op.clone(),
                Box::new(self.rewrite_expr_own(r, borrow_env, orig_env, copy_generics, scope)),
            ),
            Expr::UnaryOp(op, inner) => {
                if op == "*" {
                    if let Expr::Ident(name) = inner.as_ref() {
                        if borrow_env
                            .get(name)
                            .and_then(borrowed_box_inner_type)
                            .is_some()
                        {
                            return clone_borrowed_box_inner(name);
                        }
                    }
                }
                Expr::UnaryOp(
                    op.clone(),
                    Box::new(self.rewrite_expr_own(
                        inner,
                        borrow_env,
                        orig_env,
                        copy_generics,
                        scope,
                    )),
                )
            }
            Expr::MethodCall(receiver, method, args) => Expr::MethodCall(
                Box::new(self.rewrite_expr_own(
                    receiver,
                    borrow_env,
                    orig_env,
                    copy_generics,
                    scope,
                )),
                method.clone(),
                args.iter()
                    .map(|a| self.rewrite_expr_own(a, borrow_env, orig_env, copy_generics, scope))
                    .collect(),
            ),

            Expr::Closure(params, body, is_move) => {
                let mut inner_borrow = borrow_env.clone();
                let mut inner_orig = orig_env.clone();
                for param in params {
                    let name = closure_param_name(param);
                    if let Some(ty) = &param.ty {
                        inner_borrow.insert(name.clone(), ty.clone());
                        inner_orig.insert(name, ty.clone());
                    } else {
                        inner_borrow.remove(&name);
                        inner_orig.remove(&name);
                    }
                }
                Expr::Closure(
                    params.clone(),
                    Box::new(self.rewrite_expr_own_at(
                        body,
                        &inner_borrow,
                        &inner_orig,
                        copy_generics,
                        scope,
                        true,
                    )),
                    *is_move,
                )
            }
            Expr::TypedClosure(params, return_type, body, is_move) => {
                let mut inner_borrow = borrow_env.clone();
                let mut inner_orig = orig_env.clone();
                for param in params {
                    let name = closure_param_name(param);
                    if let Some(ty) = &param.ty {
                        inner_borrow.insert(name.clone(), ty.clone());
                        inner_orig.insert(name, ty.clone());
                    } else {
                        inner_borrow.remove(&name);
                        inner_orig.remove(&name);
                    }
                }
                Expr::TypedClosure(
                    params.clone(),
                    return_type.clone(),
                    Box::new(self.rewrite_expr_own_at(
                        body,
                        &inner_borrow,
                        &inner_orig,
                        copy_generics,
                        scope,
                        true,
                    )),
                    *is_move,
                )
            }

            // Leaves and unsupported constructs: return unchanged.
            Expr::Macro(_)
            | Expr::Path(_, _)
            | Expr::Literal(_)
            | Expr::Loop(_)
            | Expr::Await(_)
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
        scope: &ModuleScope,
    ) -> Expr {
        match arg {
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                if let Expr::Ident(name) = receiver.as_ref() {
                    if let Some(bty) = borrow_env.get(name) {
                        if is_reference_type(bty) {
                            // v: &T → v (drop clone)
                            return Expr::Ident(name.clone());
                        }
                    }
                    // The explicit clone existed only to satisfy the original
                    // owned calling convention.  This remains true when the
                    // local binding's type could not be reconstructed, so the
                    // borrowed interface can always use the source binding.
                    return Expr::Reference(Box::new(Expr::Ident(name.clone())), true, false);
                }
                // Recurse and wrap in &.
                let inner = self.rewrite_expr_own(arg, borrow_env, orig_env, copy_generics, scope);
                Expr::Reference(Box::new(inner), true, false)
            }
            Expr::Ident(name) => {
                if let Some(bty) = borrow_env.get(name) {
                    if is_reference_type(bty) {
                        // Already a reference: return as-is.
                        return Expr::Ident(name.clone());
                    }
                    // Copy type owned: wrap in &.
                    if self.is_copy(bty, copy_generics, scope) {
                        return Expr::Reference(Box::new(Expr::Ident(name.clone())), true, false);
                    }
                }
                // Non-Copy owned: shouldn't normally arise for a borrowable arg,
                // but fall back to &name conservatively.
                Expr::Reference(Box::new(Expr::Ident(name.clone())), true, false)
            }
            _ => {
                let inner = self.rewrite_expr_own(arg, borrow_env, orig_env, copy_generics, scope);
                Expr::Reference(Box::new(inner), true, false)
            }
        }
    }

    // ── Environment helpers ───────────────────────────────────────────────────

    /// Bind pattern variables to their field types in an ordinary TypeEnv.
    fn bind_pattern_env(
        &self,
        pattern: &str,
        expected: &Type,
        env: &mut TypeEnv,
        scope: &ModuleScope,
    ) {
        let pattern = pattern.trim();
        if pattern.is_empty() || pattern == "_" || pattern == ".." {
            return;
        }

        let pattern = strip_binding_modifiers(pattern);

        if let Some(inner) = outer_parens_inner(pattern) {
            let parts = split_top_level_commas(inner);
            if parts.len() > 1 {
                if let Type::Tuple(types) = expected {
                    for (p, t) in parts.iter().zip(types) {
                        self.bind_pattern_env(p, t, env, scope);
                    }
                }
                return;
            }
        }

        if let Some((constructor, args)) = split_constructor_pattern(pattern) {
            if let Some(field_types) = self.pattern_field_types(constructor, expected, scope) {
                for (arg, ty) in args.iter().zip(field_types.iter()) {
                    self.bind_pattern_env(arg, ty, env, scope);
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
    fn bind_pattern_env_for_borrow(
        &self,
        pattern: &str,
        expected: &Type,
        env: &mut BorrowEnv,
        scope: &ModuleScope,
    ) {
        self.bind_pattern_env(pattern, expected, env, scope);
    }

    /// Bind one pattern using the component-wise modes selected for a tuple
    /// scrutinee.  Tuple structure is preserved exactly; only the types of
    /// bindings originating from borrowed components are changed to shared
    /// references.
    fn bind_pattern_env_for_match_mode(
        &self,
        pattern: &str,
        mode: &MatchBindingMode,
        env: &mut BorrowEnv,
        scope: &ModuleScope,
    ) {
        match mode {
            MatchBindingMode::Owned(ty) => {
                self.bind_pattern_env_for_borrow(pattern, ty, env, scope);
            }
            MatchBindingMode::Borrowed(inner_ty) => {
                self.bind_pattern_env_for_borrow_match(pattern, inner_ty, env, scope);
            }
            MatchBindingMode::Tuple(modes) => {
                let pattern = strip_binding_modifiers(pattern.trim());
                if let Some(inner) = outer_parens_inner(pattern) {
                    let parts = split_top_level_commas(inner);
                    if parts.len() == modes.len() {
                        for (part, component_mode) in parts.iter().zip(modes) {
                            self.bind_pattern_env_for_match_mode(part, component_mode, env, scope);
                        }
                        return;
                    }
                }

                // A whole-tuple variable is unusual for generated function
                // equations, but its actual Rust value contains references in
                // exactly the borrowed positions recorded by `runtime_type`.
                self.bind_pattern_env(pattern, &mode.runtime_type(), env, scope);
            }
        }
    }

    /// B-Match rule: bind pattern variables when the scrutinee has type `&D<T>`.
    ///
    /// Each field variable `y_j` gets type `&F_j` (a shared reference to the
    /// field type). A boxed field is therefore represented as
    /// `&Box<F_inner>` until its explicit dereference binding is rewritten.
    fn bind_pattern_env_for_borrow_match(
        &self,
        pattern: &str,
        inner_ty: &Type, // inner type D<T> (reference already stripped)
        env: &mut BorrowEnv,
        scope: &ModuleScope,
    ) {
        let pattern = pattern.trim();
        if pattern.is_empty() || pattern == "_" || pattern == ".." {
            return;
        }

        let pattern = strip_binding_modifiers(pattern);

        if let Some(inner) = outer_parens_inner(pattern) {
            let parts = split_top_level_commas(inner);
            if parts.len() > 1 {
                if let Type::Tuple(types) = inner_ty {
                    for (p, t) in parts.iter().zip(types) {
                        self.bind_pattern_env_for_borrow_match(p, t, env, scope);
                    }
                }
                return;
            }
        }

        if let Some((constructor, args)) = split_constructor_pattern(pattern) {
            if let Some(field_types) = self.pattern_field_types(constructor, inner_ty, scope) {
                for (arg, fty) in args.iter().zip(field_types.iter()) {
                    // Each field variable gets type &F_j (reference to field type).
                    let ref_ty = make_ref_type(fty);
                    let sub_pattern = arg.trim();
                    let var = strip_binding_modifiers(sub_pattern);
                    if var.is_empty() || var == "_" || var == ".." {
                        // nothing
                    } else if is_binding_ident(var) {
                        env.insert(var.to_string(), ref_ty);
                    } else {
                        // Nested constructor pattern: recurse.
                        self.bind_pattern_env_for_borrow_match(var, fty, env, scope);
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

    fn infer_type(&self, expr: &Expr, env: &TypeEnv, scope: &ModuleScope) -> Option<Type> {
        match expr {
            Expr::Ident(name) => env.get(name).cloned(),
            Expr::Path(path, PathType::Namespace) => {
                self.owner_for_variant_path(path, scope).map(Type::Path)
            }
            Expr::Literal(Literal::Bool(_)) => Some(Type::Named("bool".to_string())),
            Expr::Array(elems) => {
                let first = elems.first()?;
                let element_ty = self.infer_type(first, env, scope)?;
                Some(Type::Array(Box::new(element_ty), elems.len()))
            }
            Expr::Tuple(elems) => {
                let types: Option<Vec<_>> = elems
                    .iter()
                    .map(|e| self.infer_type(e, env, scope))
                    .collect();
                types.map(|ts| {
                    if ts.is_empty() {
                        Type::Unit
                    } else {
                        Type::Tuple(ts)
                    }
                })
            }
            Expr::Call(callee, _) => self
                .infer_type(callee, env, scope)
                .and_then(|ty| self.callable_return_type(&ty))
                .or_else(|| explicit_identity_return_type(callee))
                .or_else(|| {
                    match callee.as_ref() {
                        Expr::Ident(name) => self.owner_for_variant_name(name, scope),
                        Expr::Path(path, PathType::Namespace) => {
                            self.owner_for_variant_path(path, scope)
                        }
                        _ => None,
                    }
                    .map(Type::Path)
                })
                .or_else(|| {
                    self.resolve_callee_id(callee, scope, env)
                        .and_then(|id| self.fn_sigs.get(&id).map(|(_, _, ret)| ret.clone()))
                }),
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                // `v.clone()` where v: &T gives T (auto-deref clone).
                self.infer_type(receiver, env, scope).map(|ty| {
                    if let Type::Reference(inner, true, false) = ty {
                        *inner
                    } else {
                        ty
                    }
                })
            }
            Expr::UnaryOp(op, inner) if op == "*" => {
                self.infer_type(inner, env, scope).and_then(|ty| match ty {
                    Type::Generic(name, params)
                        if matches!(type_name_leaf(&name), "Rc" | "Arc" | "Box")
                            && params.len() == 1 =>
                    {
                        params.into_iter().next()
                    }
                    Type::Reference(inner, true, _) => Some(*inner),
                    _ => None,
                })
            }
            Expr::Parenthesized(inner) => self.infer_type(inner, env, scope),
            Expr::Cast(_, ty) => Some(ty.clone()),
            Expr::Block(block) => self.infer_block_type(block, env, scope),
            Expr::If {
                then_branch,
                else_branch: Some(else_branch),
                ..
            } => {
                let then_ty = self.infer_block_type(then_branch, env, scope)?;
                let else_ty = self.infer_block_type(else_branch, env, scope)?;
                same_type(&then_ty, &else_ty).then_some(then_ty)
            }
            Expr::Match {
                expr: scrutinee,
                arms,
            } => {
                let scrutinee_ty = self.infer_type(scrutinee, env, scope);
                let mut arm_types = arms.iter().map(|arm| {
                    let mut arm_env = env.clone();
                    if let Some(ty) = &scrutinee_ty {
                        self.bind_pattern_env(&arm.pattern, ty, &mut arm_env, scope);
                    }
                    self.infer_block_type(&arm.body, &arm_env, scope)
                });
                let first = arm_types.next()??;
                arm_types.try_fold(first, |expected, actual| {
                    let actual = actual?;
                    same_type(&expected, &actual).then_some(expected)
                })
            }
            _ => None,
        }
    }

    fn infer_block_type(&self, block: &Block, env: &TypeEnv, scope: &ModuleScope) -> Option<Type> {
        let mut block_env = env.clone();
        for stmt in &block.stmts {
            let Statement::Let(let_stmt) = stmt else {
                continue;
            };
            let inferred_ty = let_stmt.ty.clone().or_else(|| {
                let_stmt
                    .init
                    .as_ref()
                    .and_then(|init| self.infer_type(init, &block_env, scope))
            });
            if let Some(ty) = inferred_ty {
                if is_binding_ident(&let_stmt.name) {
                    block_env.insert(let_stmt.name.clone(), ty);
                } else {
                    self.bind_pattern_env(&let_stmt.name, &ty, &mut block_env, scope);
                }
            }
        }
        block
            .expr
            .as_ref()
            .and_then(|expr| self.infer_type(expr, &block_env, scope))
    }

    fn callable_return_type(&self, ty: &Type) -> Option<Type> {
        match ty {
            Type::CallableTrait(callable) => Some(callable.return_type.as_ref().clone()),
            Type::Generic(name, params)
                if matches!(type_name_leaf(name), "Rc" | "Arc" | "Box") && params.len() == 1 =>
            {
                self.callable_return_type(&params[0])
            }
            Type::Reference(inner, _, _) => self.callable_return_type(inner),
            _ => None,
        }
    }

    /// Returns the field types for constructor `constructor` applied to `ty`.
    /// Both the expected datatype and the constructor owner are resolved in
    /// the current module scope, so equal leaf names in other modules cannot
    /// overwrite or suppress this lookup.
    fn pattern_field_types(
        &self,
        constructor: &str,
        ty: &Type,
        scope: &ModuleScope,
    ) -> Option<Vec<Type>> {
        let variant_name = constructor
            .rsplit("::")
            .next()
            .unwrap_or(constructor)
            .trim();

        if let Some(type_id) = self.type_id_for_type(ty, scope) {
            if let Some(def) = self.type_defs.get(&type_id) {
                let subst = type_substitution(def, ty);
                match &def.kind {
                    TypeDefKind::Enum(variants) => {
                        if let Some(v) = variants.iter().find(|v| v.name == variant_name) {
                            return Some(
                                v.fields
                                    .iter()
                                    .map(|field| self.instantiate_declared_type(def, field, &subst))
                                    .collect(),
                            );
                        }
                    }
                    TypeDefKind::Struct(fields)
                        if type_id.last().is_some_and(|name| name == variant_name)
                            || type_id
                                .last()
                                .is_some_and(|name| name == constructor.trim()) =>
                    {
                        return Some(
                            fields
                                .iter()
                                .map(|field| self.instantiate_declared_type(def, &field.ty, &subst))
                                .collect(),
                        );
                    }
                    TypeDefKind::Struct(_) => {}
                }
            }
        }

        // Try via variant owner map.
        let owner = self.owner_for_constructor(constructor, scope)?;
        let def = self.type_defs.get(&owner)?;
        match &def.kind {
            TypeDefKind::Enum(variants) => {
                variants
                    .iter()
                    .find(|v| v.name == variant_name)
                    .map(|variant| {
                        variant
                            .fields
                            .iter()
                            .map(|field| {
                                self.instantiate_declared_type(def, field, &HashMap::new())
                            })
                            .collect()
                    })
            }
            TypeDefKind::Struct(fields) => Some(
                fields
                    .iter()
                    .map(|field| self.instantiate_declared_type(def, &field.ty, &HashMap::new()))
                    .collect(),
            ),
        }
    }

    fn instantiate_declared_type(
        &self,
        def: &TypeDef,
        ty: &Type,
        subst: &HashMap<String, Type>,
    ) -> Type {
        let declared =
            canonicalize_declared_type(ty, &def.generics, &def.scope, &self.local_type_ids);
        apply_type_subst(&declared, subst)
    }

    fn owner_for_constructor(&self, constructor: &str, scope: &ModuleScope) -> Option<FunctionId> {
        let parts: Vec<String> = constructor
            .split("::")
            .map(str::trim)
            .filter(|p| !p.is_empty())
            .map(str::to_string)
            .collect();

        let resolved = scope.resolve_segments(&parts);
        if let Some(owner) = self.variant_owners.get(&resolved).cloned().flatten() {
            return Some(owner);
        }

        // A path such as `Rbt::Branch` is relative to the current module when
        // `Rbt` is not imported. `ModuleScope::resolve_segments` deliberately
        // treats other multi-segment paths as crate-root paths for generated
        // function calls, so try the lexical datatype path explicitly here.
        if !matches!(
            parts.first().map(String::as_str),
            Some("crate" | "self" | "super")
        ) && parts
            .first()
            .is_some_and(|first| !scope.imports.contains_key(first))
        {
            let mut local_variant = scope.module_path.clone();
            local_variant.extend(parts.iter().cloned());
            if let Some(owner) = self.variant_owners.get(&local_variant).cloned().flatten() {
                return Some(owner);
            }
        }

        parts
            .last()
            .and_then(|variant| self.owner_for_variant_name(variant, scope))
    }

    fn owner_for_variant_path(&self, path: &[String], scope: &ModuleScope) -> Option<FunctionId> {
        self.owner_for_constructor(&path.join("::"), scope)
    }

    fn owner_for_variant_name(
        &self,
        variant_name: &str,
        scope: &ModuleScope,
    ) -> Option<FunctionId> {
        let imported_or_local = scope.resolve_name_path(variant_name);
        if let Some(owner) = self
            .variant_owners
            .get(&imported_or_local)
            .cloned()
            .flatten()
        {
            return Some(owner);
        }

        let mut matches = self
            .variant_owners
            .iter()
            .filter(|(id, owner)| {
                owner.is_some()
                    && id.last().is_some_and(|name| name == variant_name)
                    && id.starts_with(&scope.module_path)
            })
            .filter_map(|(_, owner)| owner.clone());
        let first = matches.next()?;
        matches.all(|owner| owner == first).then_some(first)
    }

    fn type_id_for_type(&self, ty: &Type, scope: &ModuleScope) -> Option<FunctionId> {
        match ty {
            Type::Reference(inner, _, _) => self.type_id_for_type(inner, scope),
            _ => nominal_type_id(ty, scope),
        }
    }

    fn type_def_for_type(&self, ty: &Type, scope: &ModuleScope) -> Option<&TypeDef> {
        let id = self.type_id_for_type(ty, scope)?;
        self.type_defs.get(&id)
    }

    fn move_materialization(
        &self,
        ty: Option<&Type>,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> Materialization {
        if ty.is_some_and(|ty| self.can_materialize_owned(ty, copy_generics, scope)) {
            Materialization::Available
        } else {
            Materialization::Unavailable
        }
    }

    /// Whether an owned value of `ty` can be produced from `&ty` in emitted
    /// Rust. Copy evidence must be present in the emitted program (as a
    /// builtin, bound, derive, or explicit implementation), rather than merely
    /// inferred for a policy decision. Clone evidence comes from the current
    /// function bounds, source derives or explicit implementations, and
    /// supported runtime/container types.
    fn can_materialize_owned(
        &self,
        ty: &Type,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> bool {
        self.is_materialized_copy(ty, copy_generics, scope)
            || self.is_clone(ty, copy_generics, scope)
    }

    fn is_clone(&self, ty: &Type, copy_generics: &HashSet<String>, scope: &ModuleScope) -> bool {
        if self.is_materialized_copy(ty, copy_generics, scope) {
            return true;
        }

        match ty {
            Type::Named(name) => {
                if let Some(generic) = self.current_generic(scope, name) {
                    return generic_has_bound(generic, "Clone")
                        || generic_has_bound(generic, "Copy");
                }

                let type_id = nominal_type_id(ty, scope);
                type_id.as_ref().is_some_and(|id| {
                    self.derived_clone_types.contains(id)
                        || self.unconditional_clone_types.contains(id)
                        || (!self.local_type_ids.contains(id)
                            && known_unconditional_clone_type(name, scope))
                })
            }
            Type::Path(path) => nominal_type_id(ty, scope).is_some_and(|id| {
                let name = path.join("::");
                self.derived_clone_types.contains(&id)
                    || self.unconditional_clone_types.contains(&id)
                    || (!self.local_type_ids.contains(&id)
                        && known_unconditional_clone_type(&name, scope))
            }),
            Type::Generic(name, params) => {
                let leaf = type_name_leaf(name);
                let Some(type_id) = nominal_type_id(ty, scope) else {
                    return false;
                };
                if self.unconditional_clone_types.contains(&type_id) {
                    return true;
                }
                let is_local = self.local_type_ids.contains(&type_id);
                let builtin = !is_local && builtin_type_name_is_unshadowed(name, scope);
                if builtin && matches!(leaf, "Rc" | "Arc" | "Weak" | "PhantomData") {
                    return true;
                }
                if !is_local && known_unconditional_clone_type(name, scope) {
                    return true;
                }

                let clone_requires_clone_params = (builtin
                    && matches!(
                        leaf,
                        "Box"
                            | "Vec"
                            | "Option"
                            | "Result"
                            | "HashMap"
                            | "BTreeMap"
                            | "HashSet"
                            | "BTreeSet"
                            | "VecDeque"
                            | "LinkedList"
                            | "BinaryHeap"
                            | "Range"
                            | "RangeInclusive"
                    ))
                    || self.derived_clone_types.contains(&type_id);

                clone_requires_clone_params
                    && params
                        .iter()
                        .all(|param| self.is_clone(param, copy_generics, scope))
            }
            Type::Tuple(types) => types
                .iter()
                .all(|ty| self.is_clone(ty, copy_generics, scope)),
            Type::Array(inner, _) => self.is_clone(inner, copy_generics, scope),
            Type::Reference(_, true, false) | Type::Unit | Type::Never => true,
            Type::Reference(_, _, _) | Type::Slice(_) | Type::CallableTrait(_) => false,
        }
    }

    fn current_generic<'a>(
        &'a self,
        scope: &ModuleScope,
        generic_name: &str,
    ) -> Option<&'a GenericParam> {
        scope
            .current_function
            .as_ref()
            .and_then(|id| self.fn_sigs.get(id))
            .and_then(|(generics, _, _)| {
                generics.iter().find(|generic| generic.name == generic_name)
            })
    }

    fn is_copy(&self, ty: &Type, copy_generics: &HashSet<String>, scope: &ModuleScope) -> bool {
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
                ) || self.inferred_copy_types.contains(name)
                    || self.source_copy_types.contains(name)
                    || copy_generics.contains(name)
            }
            Type::Generic(name, params) => {
                let leaf = type_name_leaf(name);
                let is_local =
                    nominal_type_id(ty, scope).is_some_and(|id| self.local_type_ids.contains(&id));
                (leaf == "PhantomData" && !is_local)
                    || self.unconditional_copy_types.contains(leaf)
                    || ((self.inferred_copy_types.contains(leaf)
                        || self.source_copy_types.contains(leaf))
                        && params.iter().all(|p| self.is_copy(p, copy_generics, scope)))
            }
            Type::Tuple(types) => types.iter().all(|t| self.is_copy(t, copy_generics, scope)),
            // Rust shared references are `Copy`; mutable references are not.
            Type::Reference(_, true, false) => true,
            Type::Reference(_, _, _) => false,
            Type::Unit | Type::Never => true,
            _ => false,
        }
    }

    /// Whether Rust can perform an implicit copy in the emitted program. This
    /// remains distinct from `is_copy` so only implementations materialized in
    /// the AST can license `*shared_ref` rewrites.
    fn is_materialized_copy(
        &self,
        ty: &Type,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> bool {
        match ty {
            Type::Named(name) => {
                primitive_size_words(name).is_some()
                    || copy_generics.contains(name)
                    || self
                        .current_generic(scope, name)
                        .is_some_and(|generic| generic_has_bound(generic, "Copy"))
                    || nominal_type_id(ty, scope)
                        .is_some_and(|id| self.materialized_copy_type_ids.contains(&id))
            }
            Type::Path(path) => {
                path.last()
                    .is_some_and(|name| primitive_size_words(name).is_some())
                    || nominal_type_id(ty, scope)
                        .is_some_and(|id| self.materialized_copy_type_ids.contains(&id))
            }
            Type::Generic(name, params) => {
                let leaf = type_name_leaf(name);
                let Some(type_id) = nominal_type_id(ty, scope) else {
                    return false;
                };
                let builtin = !self.local_type_ids.contains(&type_id)
                    && builtin_type_name_is_unshadowed(name, scope);
                (leaf == "PhantomData" && builtin)
                    || self
                        .materialized_unconditional_copy_type_ids
                        .contains(&type_id)
                    || (self.materialized_copy_type_ids.contains(&type_id)
                        && params
                            .iter()
                            .all(|param| self.is_materialized_copy(param, copy_generics, scope)))
            }
            Type::Tuple(types) => types
                .iter()
                .all(|ty| self.is_materialized_copy(ty, copy_generics, scope)),
            Type::Array(inner, _) => self.is_materialized_copy(inner, copy_generics, scope),
            Type::Reference(_, true, false) => true,
            Type::Reference(_, _, _) => false,
            Type::Unit | Type::Never => true,
            _ => false,
        }
    }

    fn prefer_by_value(
        &self,
        ty: &Type,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> bool {
        const MAX_BY_VALUE_WORDS: usize = 2;
        self.is_copy(ty, copy_generics, scope)
            && self
                .estimated_size_words(ty, copy_generics, scope, &mut HashSet::new())
                .is_some_and(|words| words <= MAX_BY_VALUE_WORDS)
    }

    fn prefer_copy_match_by_value(
        &self,
        ty: &Type,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
    ) -> bool {
        // A match immediately inspects the whole discriminant/payload and is
        // more tolerant of a register-sized materialisation than a general
        // call boundary.  In particular, an `Option<RustWord<_>>` contains a
        // two-word u128 payload plus an enum tag and is therefore matched by
        // reference instead of materialising the complete value.
        const MAX_MATCH_BY_VALUE_WORDS: usize = 2;
        self.estimated_size_words(ty, copy_generics, scope, &mut HashSet::new())
            .is_some_and(|words| words <= MAX_MATCH_BY_VALUE_WORDS)
    }

    fn estimated_size_words(
        &self,
        ty: &Type,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
        visiting: &mut HashSet<FunctionId>,
    ) -> Option<usize> {
        match ty {
            Type::Named(name) if copy_generics.contains(name) => None,
            Type::Named(name) => primitive_size_words(name)
                .or_else(|| self.estimated_local_type_size(ty, copy_generics, scope, visiting)),
            Type::Path(path) => path.last().and_then(|name| {
                primitive_size_words(name)
                    .or_else(|| self.estimated_local_type_size(ty, copy_generics, scope, visiting))
            }),
            Type::Generic(name, _)
                if type_name_leaf(name) == "PhantomData"
                    && nominal_type_id(ty, scope)
                        .is_some_and(|id| !self.local_type_ids.contains(&id)) =>
            {
                Some(0)
            }
            Type::Generic(_, _) => {
                self.estimated_local_type_size(ty, copy_generics, scope, visiting)
            }
            Type::Tuple(types) => sum_estimated_words(
                types
                    .iter()
                    .map(|field| self.estimated_size_words(field, copy_generics, scope, visiting)),
            ),
            Type::Array(inner, len) => self
                .estimated_size_words(inner, copy_generics, scope, visiting)
                .and_then(|words| words.checked_mul(*len)),
            Type::Reference(_, _, _) => Some(1),
            Type::Unit | Type::Never => Some(0),
            Type::CallableTrait(_) | Type::Slice(_) => None,
        }
    }

    fn estimated_local_type_size(
        &self,
        instantiated: &Type,
        copy_generics: &HashSet<String>,
        scope: &ModuleScope,
        visiting: &mut HashSet<FunctionId>,
    ) -> Option<usize> {
        let type_id = self.type_id_for_type(instantiated, scope)?;
        if !visiting.insert(type_id.clone()) {
            return None;
        }
        let result = self.type_defs.get(&type_id).and_then(|def| {
            let subst = type_substitution(def, instantiated);
            match &def.kind {
                TypeDefKind::Struct(fields) => sum_estimated_words(fields.iter().map(|field| {
                    let ty = self.instantiate_declared_type(def, &field.ty, &subst);
                    self.estimated_size_words(&ty, copy_generics, scope, visiting)
                })),
                TypeDefKind::Enum(variants) => {
                    let mut largest = 0usize;
                    for variant in variants {
                        let payload = sum_estimated_words(variant.fields.iter().map(|field| {
                            let ty = self.instantiate_declared_type(def, field, &subst);
                            self.estimated_size_words(&ty, copy_generics, scope, visiting)
                        }))?;
                        largest = largest.max(payload);
                    }
                    1usize.checked_add(largest)
                }
            }
        });
        visiting.remove(&type_id);
        result
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
    /// (the strict local safety gate and not `PreferOwned`), the whole block is
    /// replaced with a plain non-`move` closure `|x̄| { clo_bor }` where each `yj_cap` is
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
        scope: &ModuleScope,
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
                        if method == "clone" && args.is_empty() && ls.name.ends_with("_cap") {
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

        // Check borrowability: for each captured variable (`y_cap`), borrowing
        // must be safe and must not discard a profitable ownership transfer.
        // Use `in_return_ctx = true` because the closure body's tail expression
        // is the closure's return value.
        for (cap_name, _) in &captures {
            let cap_ty = env_with_caps
                .get(cap_name)
                .cloned()
                .unwrap_or_else(|| Type::Named("__unknown_capture".to_string()));
            let derived = DerivedOrigins::for_parameter(cap_name, &cap_ty, scope);
            let mut demands = HashSet::new();
            let mut env_copy = env_with_caps.clone();
            self.collect_demands_expr(
                body,
                &derived,
                &mut env_copy,
                copy_generics,
                &mut demands,
                DemandSite::new(true, scope), // closure-body tail is return context
            );
            if !local_rewrite_safe(&demands) || prefer_owned(&demands, false) {
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

/// Give direct and clone-marked matches the same ownership provenance for
/// occurrence-local demand analysis. The clone itself is an implementation
/// adaptation of the scrutinee; demands of the pattern-bound fields decide
/// whether shared decomposition is safe and profitable.
fn normalize_match_scrutinee(expr: &Expr, root: &str) -> Option<Expr> {
    let Expr::Match { arms, .. } = expr else {
        return None;
    };
    Some(Expr::Match {
        expr: Box::new(Expr::Ident(root.to_string())),
        arms: arms.clone(),
    })
}

// ── B-Closure helpers ────────────────────────────────────────────────────────

/// Extract the bare parameter name from a possibly-typed closure param string.
/// `"x"` → `"x"`, `"x: Int"` → `"x"`, `"mut x: Int"` → `"x"`.
fn closure_param_name(param: &ClosureParam) -> String {
    param.pattern.trim_start_matches("mut ").trim().to_string()
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

fn collect_closure_binding_usage_block(block: &Block, name: &str, usage: &mut ClosureBindingUsage) {
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

fn collect_closure_binding_usage_expr(expr: &Expr, name: &str, usage: &mut ClosureBindingUsage) {
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
        | Expr::Cast(inner, _)
        | Expr::UnaryOp(_, inner)
        | Expr::Reference(inner, _, _) => {
            collect_closure_binding_usage_expr(inner, name, usage);
        }
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            collect_closure_binding_usage_expr(left, name, usage);
            collect_closure_binding_usage_expr(right, name, usage);
        }
        Expr::Array(elems) | Expr::Tuple(elems) => {
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
        Expr::Closure(params, body, _) | Expr::TypedClosure(params, _, body, _) => {
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
        Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
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
        Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => false,
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
        | Expr::Cast(inner, _)
        | Expr::UnaryOp(_, inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => expr_has_free_var_from(inner, vars),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            expr_has_free_var_from(l, vars) || expr_has_free_var_from(r, vars)
        }
        Expr::Array(elems) | Expr::Tuple(elems) => {
            elems.iter().any(|e| expr_has_free_var_from(e, vars))
        }
        Expr::Match { expr, arms } => {
            expr_has_free_var_from(expr, vars)
                || arms.iter().any(|arm| {
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
        Expr::Closure(params, body, _) | Expr::TypedClosure(params, _, body, _) => {
            // Closure params shadow outer vars.
            let shadowed: HashSet<String> = params.iter().map(|p| closure_param_name(p)).collect();
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
                if ls
                    .init
                    .as_ref()
                    .map_or(false, |i| expr_has_free_var_from(i, vars))
                {
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
fn extract_move_closure_parts(expr: &Expr) -> Option<(&[ClosureParam], &Expr)> {
    match strip_parens(expr) {
        Expr::Closure(params, body, true) | Expr::TypedClosure(params, _, body, true) => {
            Some((params.as_slice(), body.as_ref()))
        }
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
            args.iter()
                .map(|a| subst_idents_in_expr(a, subst))
                .collect(),
        ),
        Expr::Call(callee, args) => Expr::Call(
            Box::new(subst_idents_in_expr(callee, subst)),
            args.iter()
                .map(|a| subst_idents_in_expr(a, subst))
                .collect(),
        ),
        Expr::Block(block) => Expr::Block(subst_idents_in_block(block, subst)),
        Expr::Parenthesized(inner) => {
            Expr::Parenthesized(Box::new(subst_idents_in_expr(inner, subst)))
        }
        Expr::Cast(inner, ty) => {
            Expr::Cast(Box::new(subst_idents_in_expr(inner, subst)), ty.clone())
        }
        Expr::Array(elems) => Expr::Array(
            elems
                .iter()
                .map(|e| subst_idents_in_expr(e, subst))
                .collect(),
        ),
        Expr::Tuple(elems) => Expr::Tuple(
            elems
                .iter()
                .map(|e| subst_idents_in_expr(e, subst))
                .collect(),
        ),
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
        Expr::TypedClosure(params, return_type, body, is_move) => {
            let mut inner_subst = subst.clone();
            for p in params {
                inner_subst.remove(&closure_param_name(p));
            }
            Expr::TypedClosure(
                params.clone(),
                return_type.clone(),
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

fn box_inner_type(ty: &Type) -> Option<&Type> {
    match ty {
        Type::Generic(name, params) if type_name_leaf(name) == "Box" && params.len() == 1 => {
            Some(&params[0])
        }
        _ => None,
    }
}

fn borrowed_box_inner_type(ty: &Type) -> Option<&Type> {
    ref_inner(ty).and_then(box_inner_type)
}

fn same_type(left: &Type, right: &Type) -> bool {
    match (left, right) {
        (Type::Path(left), Type::Path(right)) => left == right,
        (Type::Named(left), Type::Named(right)) => left == right,
        (Type::Generic(left_name, left_args), Type::Generic(right_name, right_args)) => {
            left_name == right_name
                && left_args.len() == right_args.len()
                && left_args
                    .iter()
                    .zip(right_args)
                    .all(|(left, right)| same_type(left, right))
        }
        (Type::CallableTrait(left), Type::CallableTrait(right)) => {
            let same_qualifier = matches!(
                (&left.qualifier, &right.qualifier),
                (CallableTraitQualifier::Dyn, CallableTraitQualifier::Dyn)
                    | (CallableTraitQualifier::Impl, CallableTraitQualifier::Impl)
            );
            same_qualifier
                && left.trait_name == right.trait_name
                && left.args.len() == right.args.len()
                && left
                    .args
                    .iter()
                    .zip(&right.args)
                    .all(|(left, right)| same_type(left, right))
                && same_type(&left.return_type, &right.return_type)
        }
        (
            Type::Reference(left, left_ref, left_mut),
            Type::Reference(right, right_ref, right_mut),
        ) => left_ref == right_ref && left_mut == right_mut && same_type(left, right),
        (Type::Tuple(left), Type::Tuple(right)) => {
            left.len() == right.len()
                && left
                    .iter()
                    .zip(right)
                    .all(|(left, right)| same_type(left, right))
        }
        (Type::Slice(left), Type::Slice(right)) => same_type(left, right),
        (Type::Array(left, left_len), Type::Array(right, right_len)) => {
            left_len == right_len && same_type(left, right)
        }
        (Type::Unit, Type::Unit) | (Type::Never, Type::Never) => true,
        _ => false,
    }
}

fn is_box_type(ty: &Type) -> bool {
    box_inner_type(ty).is_some()
}

fn deref_ident_name(expr: &Expr) -> Option<&str> {
    match expr {
        Expr::UnaryOp(op, inner) if op == "*" => match inner.as_ref() {
            Expr::Ident(name) => Some(name.as_str()),
            _ => None,
        },
        _ => None,
    }
}

fn borrowed_box_as_ref(name: &str) -> Expr {
    Expr::MethodCall(
        Box::new(Expr::Ident(name.to_string())),
        "as_ref".to_string(),
        vec![],
    )
}

fn clone_borrowed_box_inner(name: &str) -> Expr {
    let as_ref_call = borrowed_box_as_ref(name);
    Expr::MethodCall(Box::new(as_ref_call), "clone".to_string(), vec![])
}

fn borrowed_local_alias(expr: &Expr, env: &BorrowEnv) -> Option<(Expr, Type)> {
    match strip_parens(expr) {
        Expr::Ident(name) => env
            .get(name)
            .filter(|ty| is_reference_type(ty))
            .map(|ty| (Expr::Ident(name.clone()), ty.clone())),
        deref => borrowed_box_deref_alias(deref, env),
    }
}

fn borrowed_box_deref_alias(expr: &Expr, env: &BorrowEnv) -> Option<(Expr, Type)> {
    let name = deref_ident_name(expr)?;
    let inner_ty = env.get(name).and_then(borrowed_box_inner_type)?;
    Some((borrowed_box_as_ref(name), make_ref_type(inner_ty)))
}

fn nominal_type_id(ty: &Type, scope: &ModuleScope) -> Option<FunctionId> {
    match ty {
        Type::Named(name) | Type::Generic(name, _) => {
            let segments = name
                .split("::")
                .map(str::trim)
                .filter(|segment| !segment.is_empty())
                .map(str::to_string)
                .collect::<Vec<_>>();
            if segments.len() == 1 {
                Some(scope.resolve_name_path(strip_path_segment_generics(&segments[0])))
            } else if segments.is_empty() {
                None
            } else {
                Some(scope.resolve_segments(&segments))
            }
        }
        Type::Path(path) => Some(scope.resolve_segments(path)),
        _ => None,
    }
}

fn unconditional_impl_target_id(impl_block: &ImplBlock, scope: &ModuleScope) -> Option<FunctionId> {
    if impl_block
        .generics
        .iter()
        .any(|generic| !generic.bounds.is_empty())
    {
        return None;
    }

    match &impl_block.target {
        Type::Named(_) | Type::Path(_) if impl_block.generics.is_empty() => {
            nominal_type_id(&impl_block.target, scope)
        }
        Type::Generic(_, args) if args.len() == impl_block.generics.len() => {
            let impl_generics = impl_block
                .generics
                .iter()
                .map(|generic| generic.name.as_str())
                .collect::<HashSet<_>>();
            let target_generics = args
                .iter()
                .map(|arg| match arg {
                    Type::Named(name) => Some(name.as_str()),
                    _ => None,
                })
                .collect::<Option<HashSet<_>>>()?;
            (impl_generics == target_generics)
                .then(|| nominal_type_id(&impl_block.target, scope))?
        }
        _ => None,
    }
}

fn type_name_leaf(name: &str) -> &str {
    name.rsplit("::").next().unwrap_or(name)
}

/// Canonical outer nominal constructor, without generic arguments.
fn outer_nominal_family(ty: &Type) -> Option<String> {
    match ty {
        Type::Named(name) | Type::Generic(name, _) => {
            Some(strip_path_segment_generics(name).to_string())
        }
        Type::Path(path) => Some(
            path.iter()
                .map(|segment| strip_path_segment_generics(segment))
                .collect::<Vec<_>>()
                .join("::"),
        ),
        _ => None,
    }
}

fn outer_nominal_family_in_scope(ty: &Type, scope: &ModuleScope) -> Option<String> {
    nominal_type_id(ty, scope)
        .map(|id| id.join("::"))
        .or_else(|| outer_nominal_family(ty))
}

fn same_outer_nominal_family_in_scope(left: &Type, right: &Type, scope: &ModuleScope) -> bool {
    outer_nominal_family_in_scope(left, scope)
        .zip(outer_nominal_family_in_scope(right, scope))
        .is_some_and(|(left, right)| left == right)
}

/// Whether an owned field carries the root nominal family through an owning
/// aggregate. References and callable signatures only mention a type and do
/// not transfer its ownership.
fn type_carries_nominal_family(ty: &Type, family: &str) -> bool {
    if outer_nominal_family(ty).as_deref() == Some(family) {
        return true;
    }
    match ty {
        Type::Generic(_, params) | Type::Tuple(params) => params
            .iter()
            .any(|param| type_carries_nominal_family(param, family)),
        Type::Array(inner, _) => type_carries_nominal_family(inner, family),
        Type::Named(_)
        | Type::Path(_)
        | Type::Slice(_)
        | Type::Reference(_, _, _)
        | Type::CallableTrait(_)
        | Type::Unit
        | Type::Never => false,
    }
}

fn type_is_copy_trait(ty: &Type) -> bool {
    match ty {
        Type::Named(name) => name == "Copy",
        Type::Path(path) => path.last().is_some_and(|name| name == "Copy"),
        _ => false,
    }
}

fn type_is_clone_trait(ty: &Type) -> bool {
    match ty {
        Type::Named(name) => name == "Clone",
        Type::Path(path) => path.last().is_some_and(|name| name == "Clone"),
        _ => false,
    }
}

fn generic_has_bound(generic: &GenericParam, wanted_bound: &str) -> bool {
    generic
        .bounds
        .iter()
        .any(|bound| type_name_leaf(bound.trim()) == wanted_bound)
}

fn written_or_imported_path_has_root(
    written_name: &str,
    scope: &ModuleScope,
    wanted_root: &str,
) -> bool {
    if written_name.contains("::") {
        return written_name
            .split("::")
            .map(str::trim)
            .find(|segment| !segment.is_empty())
            .is_some_and(|root| strip_path_segment_generics(root) == wanted_root);
    }

    let leaf = type_name_leaf(written_name);
    scope
        .imports
        .get(leaf)
        .and_then(|path| path.first())
        .is_some_and(|root| strip_path_segment_generics(root) == wanted_root)
}

fn builtin_type_name_is_unshadowed(written_name: &str, scope: &ModuleScope) -> bool {
    let leaf = type_name_leaf(written_name);
    if scope.imports.contains_key(leaf) || written_name.contains("::") {
        return ["std", "core", "alloc"]
            .iter()
            .any(|root| written_or_imported_path_has_root(written_name, scope, root));
    }

    // Unqualified built-in/prelude spellings are valid unless a package-local
    // nominal type with the resolved identity was collected; the caller checks
    // that condition before consulting this helper.
    true
}

/// Clone implementations supplied by Rust's prelude or the fixed runtime used
/// by generated Isabelle code.  Local derived/explicit implementations are
/// recorded separately in `BorrowContext`.
fn known_unconditional_clone_type(written_name: &str, scope: &ModuleScope) -> bool {
    match type_name_leaf(written_name) {
        "String" => builtin_type_name_is_unshadowed(written_name, scope),
        "BigInt" | "BigUint" => {
            written_or_imported_path_has_root(written_name, scope, "num_bigint")
        }
        "BigRational" => written_or_imported_path_has_root(written_name, scope, "num_rational"),
        _ => false,
    }
}

fn primitive_size_words(name: &str) -> Option<usize> {
    match name {
        "bool" | "char" | "i8" | "i16" | "i32" | "i64" | "isize" | "u8" | "u16" | "u32" | "u64"
        | "usize" | "f32" | "f64" => Some(1),
        "i128" | "u128" => Some(2),
        _ => None,
    }
}

fn sum_estimated_words(mut values: impl Iterator<Item = Option<usize>>) -> Option<usize> {
    values.try_fold(0usize, |total, value| total.checked_add(value?))
}

fn contains_callable_trait(ty: &Type) -> bool {
    match ty {
        Type::CallableTrait(_) => true,
        Type::Generic(_, params) | Type::Tuple(params) => {
            params.iter().any(contains_callable_trait)
        }
        Type::Slice(inner) | Type::Array(inner, _) | Type::Reference(inner, _, _) => {
            contains_callable_trait(inner)
        }
        Type::Path(_) | Type::Named(_) | Type::Unit | Type::Never => false,
    }
}

/// Resolve nominal field types in the scope where their datatype was
/// declared.  Pattern bindings are later analysed in the caller's scope; if
/// the spelling were left unqualified, a same-named caller-local type could
/// incorrectly provide (or hide) Copy/Clone evidence.
fn canonicalize_declared_type(
    ty: &Type,
    generics: &[String],
    scope: &ModuleScope,
    local_type_ids: &HashSet<FunctionId>,
) -> Type {
    match ty {
        Type::Named(name) => {
            let canonical =
                canonicalize_declared_nominal_name(name, generics, scope, local_type_ids);
            if canonical == *name {
                ty.clone()
            } else {
                Type::Path(canonical.split("::").map(str::to_string).collect())
            }
        }
        Type::Path(path) => {
            let written = path.join("::");
            let canonical =
                canonicalize_declared_nominal_name(&written, generics, scope, local_type_ids);
            Type::Path(canonical.split("::").map(str::to_string).collect())
        }
        Type::Generic(name, params) => Type::Generic(
            canonicalize_declared_nominal_name(name, generics, scope, local_type_ids),
            params
                .iter()
                .map(|param| canonicalize_declared_type(param, generics, scope, local_type_ids))
                .collect(),
        ),
        Type::Tuple(types) => Type::Tuple(
            types
                .iter()
                .map(|ty| canonicalize_declared_type(ty, generics, scope, local_type_ids))
                .collect(),
        ),
        Type::Array(inner, len) => Type::Array(
            Box::new(canonicalize_declared_type(
                inner,
                generics,
                scope,
                local_type_ids,
            )),
            *len,
        ),
        Type::Reference(inner, is_ref, mutable) => Type::Reference(
            Box::new(canonicalize_declared_type(
                inner,
                generics,
                scope,
                local_type_ids,
            )),
            *is_ref,
            *mutable,
        ),
        Type::Slice(inner) => Type::Slice(Box::new(canonicalize_declared_type(
            inner,
            generics,
            scope,
            local_type_ids,
        ))),
        Type::CallableTrait(callable) => Type::CallableTrait(CallableTraitType {
            qualifier: callable.qualifier.clone(),
            trait_name: callable.trait_name.clone(),
            args: callable
                .args
                .iter()
                .map(|arg| canonicalize_declared_type(arg, generics, scope, local_type_ids))
                .collect(),
            return_type: Box::new(canonicalize_declared_type(
                &callable.return_type,
                generics,
                scope,
                local_type_ids,
            )),
        }),
        Type::Unit | Type::Never => ty.clone(),
    }
}

fn canonicalize_declared_nominal_name(
    name: &str,
    generics: &[String],
    scope: &ModuleScope,
    local_type_ids: &HashSet<FunctionId>,
) -> String {
    let segments = name
        .split("::")
        .map(str::trim)
        .filter(|segment| !segment.is_empty())
        .map(str::to_string)
        .collect::<Vec<_>>();
    let Some(leaf) = segments.last().map(String::as_str) else {
        return name.to_string();
    };

    if segments.len() == 1 {
        if generics.iter().any(|generic| generic == leaf) || primitive_size_words(leaf).is_some() {
            return name.to_string();
        }
        if let Some(imported) = scope.imports.get(leaf) {
            let resolved = scope.resolve_segments(imported);
            let explicitly_relative = matches!(
                imported.first().map(String::as_str),
                Some("crate" | "self" | "super")
            );
            return if explicitly_relative || local_type_ids.contains(&resolved) {
                resolved.join("::")
            } else {
                imported.join("::")
            };
        }

        let local_id = scope.resolve_name_path(leaf);
        if local_type_ids.contains(&local_id) {
            return local_id.join("::");
        }

        return match leaf {
            "String" => "std::string::String".to_string(),
            "Box" => "std::boxed::Box".to_string(),
            "Vec" => "std::vec::Vec".to_string(),
            "Option" => "std::option::Option".to_string(),
            "Result" => "std::result::Result".to_string(),
            _ => name.to_string(),
        };
    }

    let resolved = scope.resolve_segments(&segments);
    if local_type_ids.contains(&resolved) {
        resolved.join("::")
    } else {
        name.to_string()
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
        Type::Array(inner, len) => Type::Array(Box::new(apply_type_subst(inner, subst)), *len),
        Type::Reference(inner, is_ref, mutable) => {
            Type::Reference(Box::new(apply_type_subst(inner, subst)), *is_ref, *mutable)
        }
        Type::Slice(inner) => Type::Slice(Box::new(apply_type_subst(inner, subst))),
        Type::CallableTrait(callable) => Type::CallableTrait(CallableTraitType {
            qualifier: callable.qualifier.clone(),
            trait_name: callable.trait_name.clone(),
            args: callable
                .args
                .iter()
                .map(|arg| apply_type_subst(arg, subst))
                .collect(),
            return_type: Box::new(apply_type_subst(&callable.return_type, subst)),
        }),
        Type::Path(_) | Type::Unit | Type::Never => ty.clone(),
    }
}

fn collect_imports(items: &[Item]) -> HashMap<String, Vec<String>> {
    let mut imports = HashMap::new();
    for item in items {
        if let Item::Use(use_stmt) = item {
            collect_import(&mut imports, use_stmt);
        }
    }
    imports
}

fn collect_import(imports: &mut HashMap<String, Vec<String>>, use_stmt: &UseStatement) {
    match &use_stmt.kind {
        UseKind::Simple => {
            if let Some((source, local)) = imported_leaf(use_stmt.path.last()) {
                let mut path = use_stmt.path.clone();
                if let Some(last) = path.last_mut() {
                    *last = source;
                }
                imports.insert(local, path);
            }
        }
        UseKind::Nested(items) => {
            for item in items {
                if let Some((source, local)) = imported_leaf(Some(item)) {
                    let mut path = use_stmt.path.clone();
                    path.push(source);
                    imports.insert(local, path);
                }
            }
        }
        UseKind::Glob => {}
    }
}

fn imported_leaf(leaf: Option<&String>) -> Option<(String, String)> {
    let leaf = leaf?.trim();
    if let Some((source, local)) = leaf.split_once(" as ") {
        Some((source.trim().to_string(), local.trim().to_string()))
    } else {
        Some((leaf.to_string(), leaf.to_string()))
    }
}

fn explicit_identity_return_type(callee: &Expr) -> Option<Type> {
    let segment = match callee {
        Expr::Ident(segment) => segment,
        Expr::Path(path, PathType::Namespace) => path.last()?,
        Expr::Parenthesized(inner) => return explicit_identity_return_type(inner),
        _ => return None,
    };
    (strip_path_segment_generics(segment) == "identity")
        .then(|| crate::rustlight_parser::first_explicit_type_argument(segment))
        .flatten()
}

fn strip_path_segment_generics(segment: &str) -> &str {
    let before_args = segment.split_once('<').map_or(segment, |(head, _)| head);
    before_args
        .trim()
        .strip_suffix("::")
        .unwrap_or(before_args.trim())
        .trim()
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

/// Whether `expr` preserves a borrow-derived origin in a local binding.
///
/// These are precisely the alias shapes that remain references when B-Match
/// rewrites an owned datatype traversal to a shared one. Owned materializations
/// such as `.clone()` deliberately do not propagate derivedness.
fn derived_borrow_alias_origin(expr: &Expr, derived: &DerivedOrigins) -> Option<Origin> {
    match strip_parens(expr) {
        Expr::Ident(name) => derived.origin(name),
        Expr::UnaryOp(op, inner) if op == "*" => match strip_parens(inner) {
            Expr::Ident(name) => derived.origin(name),
            _ => None,
        },
        Expr::MethodCall(receiver, method, args) if method == "as_ref" && args.is_empty() => {
            match strip_parens(receiver) {
                Expr::Ident(name) => derived.origin(name),
                _ => None,
            }
        }
        Expr::Reference(inner, true, false) => match strip_parens(inner) {
            Expr::Ident(name) => derived.origin(name),
            _ => None,
        },
        _ => None,
    }
}

/// Untyped local aliases that the body rewriter can keep as shared values.
/// Besides a direct `let y = x`, the generator's `let y = *boxed` traversal
/// becomes `let y = boxed.as_ref()` after B-Match.
fn supported_let_alias_origin(
    expr: &Expr,
    derived: &DerivedOrigins,
    env: &TypeEnv,
) -> Option<Origin> {
    match strip_parens(expr) {
        Expr::Ident(name) => derived.origin(name),
        Expr::UnaryOp(op, inner) if op == "*" => match strip_parens(inner) {
            Expr::Ident(name) if env.get(name).is_some_and(is_box_type) => derived.origin(name),
            _ => None,
        },
        _ => None,
    }
}

fn collect_deref_box_binding_names_from_body(
    pattern: &str,
    body: &Block,
    out: &mut HashSet<String>,
) {
    let mut bindings = HashSet::new();
    collect_pattern_binding_names(pattern, &mut bindings);
    if bindings.is_empty() {
        return;
    }

    let mut derefs = HashSet::new();
    collect_deref_ident_uses_block(body, &mut derefs);
    for name in bindings.intersection(&derefs) {
        out.insert(name.clone());
    }
}

fn mark_deref_box_bindings_from_body(pattern: &str, body: &Block, env: &mut BorrowEnv) {
    let mut boxed_bindings = HashSet::new();
    collect_deref_box_binding_names_from_body(pattern, body, &mut boxed_bindings);
    for name in boxed_bindings {
        env.entry(name.clone())
            .or_insert_with(synthetic_borrowed_box_type);
    }
}

fn synthetic_borrowed_box_type() -> Type {
    make_ref_type(&Type::Generic("Box".to_string(), vec![Type::Never]))
}

fn collect_pattern_binding_names(pattern: &str, out: &mut HashSet<String>) {
    let pattern = pattern.trim();
    if pattern.is_empty() || pattern == "_" || pattern == ".." {
        return;
    }

    let pattern = strip_binding_modifiers(pattern);

    if let Some(inner) = outer_parens_inner(pattern) {
        let parts = split_top_level_commas(inner);
        if parts.len() > 1 {
            for part in parts {
                collect_pattern_binding_names(&part, out);
            }
            return;
        }
    }

    if let Some((_, args)) = split_constructor_pattern(pattern) {
        for arg in args {
            collect_pattern_binding_names(&arg, out);
        }
        return;
    }

    if pattern.contains("::") || matches!(pattern, "true" | "false") {
        return;
    }

    if is_binding_ident(pattern) {
        out.insert(pattern.to_string());
    }
}

fn collect_deref_ident_uses_block(block: &Block, out: &mut HashSet<String>) {
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &let_stmt.init {
                    collect_deref_ident_uses_expr(init, out);
                }
            }
            Statement::Expr(expr) => collect_deref_ident_uses_expr(expr, out),
            Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {
            }
        }
    }
    if let Some(expr) = &block.expr {
        collect_deref_ident_uses_expr(expr, out);
    }
}

fn collect_deref_ident_uses_expr(expr: &Expr, out: &mut HashSet<String>) {
    match expr {
        Expr::UnaryOp(op, inner) if op == "*" => {
            if let Expr::Ident(name) = inner.as_ref() {
                out.insert(name.clone());
            } else {
                collect_deref_ident_uses_expr(inner, out);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            collect_deref_ident_uses_expr(receiver, out);
            for arg in args {
                collect_deref_ident_uses_expr(arg, out);
            }
        }
        Expr::Call(callee, args) => {
            collect_deref_ident_uses_expr(callee, out);
            for arg in args {
                collect_deref_ident_uses_expr(arg, out);
            }
        }
        Expr::Block(block) => {
            collect_deref_ident_uses_block(block, out);
        }
        Expr::Loop(block) | Expr::Unsafe(block) => {
            collect_deref_ident_uses_block(block, out);
        }
        Expr::Await(inner)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Reference(inner, _, _)
        | Expr::UnaryOp(_, inner) => collect_deref_ident_uses_expr(inner, out),
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            collect_deref_ident_uses_expr(left, out);
            collect_deref_ident_uses_expr(right, out);
        }
        Expr::Array(elems) | Expr::Tuple(elems) => {
            for elem in elems {
                collect_deref_ident_uses_expr(elem, out);
            }
        }
        Expr::Match { expr, arms } => {
            collect_deref_ident_uses_expr(expr, out);
            for arm in arms {
                if let Some(guard) = &arm.guard {
                    collect_deref_ident_uses_expr(guard, out);
                }
                collect_deref_ident_uses_block(&arm.body, out);
            }
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            collect_deref_ident_uses_expr(condition, out);
            collect_deref_ident_uses_block(then_branch, out);
            if let Some(else_branch) = else_branch {
                collect_deref_ident_uses_block(else_branch, out);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            collect_deref_ident_uses_expr(value, out);
            collect_deref_ident_uses_block(then_branch, out);
            if let Some(else_branch) = else_branch {
                collect_deref_ident_uses_block(else_branch, out);
            }
        }
        Expr::Closure(_, body, _) | Expr::TypedClosure(_, _, body, _) => {
            collect_deref_ident_uses_expr(body, out)
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    collect_deref_ident_uses_expr(closure, out);
                }
            }
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }
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
    use crate::{optimize_copy, optimize_last_use, parse_rust_source};
    use rustlightast::RustCodeGenerator;

    fn named(name: &str) -> Type {
        Type::Named(name.to_string())
    }

    fn lit_i(value: i64) -> Expr {
        Expr::Literal(Literal::Int(value))
    }

    fn clone_call(name: &str) -> Expr {
        Expr::MethodCall(
            Box::new(Expr::Ident(name.to_string())),
            "clone".to_string(),
            vec![],
        )
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

    fn test_scope() -> ModuleScope {
        ModuleScope {
            module_path: vec!["crate".to_string(), "Test".to_string()],
            imports: HashMap::new(),
            current_function: None,
        }
    }

    fn tree_enum() -> Item {
        Item::Enum(EnumDef {
            name: "Tree".to_string(),
            variants: vec![
                Variant {
                    name: "Leaf".to_string(),
                    data: None,
                    docs: vec![],
                },
                Variant {
                    name: "Branch".to_string(),
                    data: None,
                    docs: vec![],
                },
            ],
            generics: vec![],
            derives: vec![],
            docs: vec![],
            vis: Visibility::Public,
        })
    }

    fn leaf_match_body(param: &str) -> Block {
        block_tail(Expr::Match {
            expr: Box::new(Expr::Ident(param.to_string())),
            arms: vec![
                MatchArm {
                    pattern: "Tree::Leaf".to_string(),
                    guard: None,
                    body: block_tail(Expr::Literal(Literal::Bool(true))),
                },
                MatchArm {
                    pattern: "Tree::Branch".to_string(),
                    guard: None,
                    body: block_tail(Expr::Literal(Literal::Bool(false))),
                },
            ],
        })
    }

    fn tuple_leaf_match_body(left: &str, right: &str) -> Block {
        block_tail(Expr::Match {
            expr: Box::new(Expr::Tuple(vec![
                Expr::Ident(left.to_string()),
                Expr::Ident(right.to_string()),
            ])),
            arms: vec![
                MatchArm {
                    pattern: "(Tree::Leaf, Tree::Leaf)".to_string(),
                    guard: None,
                    body: block_tail(Expr::Literal(Literal::Bool(true))),
                },
                MatchArm {
                    pattern: "(_, _)".to_string(),
                    guard: None,
                    body: block_tail(Expr::Literal(Literal::Bool(false))),
                },
            ],
        })
    }

    fn empty_ctx() -> BorrowContext {
        BorrowContext {
            inferred_copy_types: HashSet::new(),
            source_copy_types: HashSet::new(),
            materialized_copy_type_ids: HashSet::new(),
            unconditional_copy_types: HashSet::new(),
            materialized_unconditional_copy_type_ids: HashSet::new(),
            derived_clone_types: HashSet::new(),
            unconditional_clone_types: HashSet::new(),
            local_type_ids: HashSet::new(),
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
                vec![ClosureParam::typed("x", named("i32"))],
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
        ctx.rewrite_block_borrow(
            block,
            &mut borrow_env,
            &orig_env,
            &HashSet::new(),
            &test_scope(),
        )
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
    fn borrowed_box_deref_alias_keeps_let_binding_borrowed() {
        let env = HashMap::from([(
            "p0".to_string(),
            make_ref_type(&Type::Generic("Box".to_string(), vec![named("Option")])),
        )]);
        let expr = Expr::UnaryOp("*".to_string(), Box::new(Expr::Ident("p0".to_string())));

        let (alias, alias_ty) = borrowed_box_deref_alias(&expr, &env).expect("borrowed box alias");

        assert!(matches!(
            alias,
            Expr::MethodCall(receiver, method, args)
                if matches!(receiver.as_ref(), Expr::Ident(name) if name == "p0")
                    && method == "as_ref"
                    && args.is_empty()
        ));
        assert!(matches!(
            alias_ty,
            Type::Reference(inner, true, false)
                if matches!(inner.as_ref(), Type::Named(name) if name == "Option")
        ));
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
    fn concrete_datatype_param_is_considered_for_borrowing() {
        let body = leaf_match_body("x");
        let mut module = RustModule {
            name: "Test".to_string(),
            docs: vec![],
            items: vec![
                tree_enum(),
                Item::Function(function("is_leaf", "x", named("Tree"), body)),
            ],
            attrs: vec![],
            vis: Visibility::Public,
        };

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Test::is_leaf"));
        let Item::Function(function) = &module.items[1] else {
            panic!("expected function");
        };
        assert!(is_reference_type(&function.params[0].ty));
    }

    #[test]
    fn last_use_clone_keeps_recursive_structure_parameter_owned() {
        let source = r#"
#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons(A, Box<List<A>>),
}

pub fn bubble_min<A>(x0: List<A>) -> List<A>
where
    A: Clone + 'static,
{
    match x0 {
        List::Nil => List::Nil,
        List::Cons(v, p1a) => {
            let va = *p1a;
            bubble_min(List::Cons(v.clone(), Box::new(va.clone())))
        }
    }
}
"#;
        let mut module = parse_rust_source(source, "Bubblesort_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(!analysis.borrow_fns.contains("bubble_min"));
        let Item::Function(function) = &module.items[1] else {
            panic!("expected bubble_min function");
        };
        assert!(!is_reference_type(&function.params[0].ty));

        // Borrow analysis only consults the move opportunity. Last-Use performs
        // the actual rewrite later, once the parameter has remained owned.
        optimize_last_use(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(!printed.contains("v.clone()"));
        assert!(!printed.contains("va.clone()"));
        assert!(printed.contains("List::Cons(v, Box::new(va))"));
    }

    #[test]
    fn rebuilding_recursive_family_with_payload_transfer_keeps_parameter_owned() {
        let source = r#"
#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons(A, Box<List<A>>),
}

pub fn mapa<B, A>(f: Rc<dyn Fn(A) -> B>, x0: List<A>) -> List<B>
where
    A: Clone + 'static,
    B: Clone + 'static,
{
    match x0 {
        List::Nil => List::Nil,
        List::Cons(x, p0a) => {
            let xs = *p0a;
            List::Cons((*f)(x.clone()), Box::new(mapa(f.clone(), xs.clone())))
        }
    }
}
"#;
        let mut module = parse_rust_source(source, "Map_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(!analysis.borrow_fns.contains("crate::Map_Test::mapa"));
        optimize_last_use(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(
            printed.contains("pub fn mapa<B, A>(f: Rc<dyn Fn(A) -> B>, x0: List<A>) -> List<B>")
        );
        assert!(printed.contains("List::Cons((*f)(x), Box::new(mapa(f, xs)))"));
        assert!(!printed.contains("x.clone()"));
        assert!(!printed.contains("xs.clone()"));
    }

    #[test]
    fn preferred_owned_clone_match_survives_until_last_use_move() {
        let source = r#"
#[derive(Clone)]
pub struct Blob(pub Box<u64>);

#[derive(Clone)]
pub enum Outcome {
    Stuck,
    Next(Blob, Blob),
}

pub fn consume(left: Blob, right: Blob) -> Outcome {
    Outcome::Next(left, right)
}

pub fn step(st: Outcome) -> Outcome {
    match st.clone() {
        Outcome::Stuck => Outcome::Stuck,
        Outcome::Next(left, right) => consume(left.clone(), right.clone()),
    }
}
"#;
        let mut module = parse_rust_source(source, "Step_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(!analysis.borrow_fns.contains("crate::Step_Test::step"));
        optimize_last_use(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn step(st: Outcome) -> Outcome"));
        assert!(printed.contains("match st {"));
        assert!(printed.contains("consume(left, right)"));
        assert!(!printed.contains("match &st"));
        assert!(!printed.contains("left.clone()"));
        assert!(!printed.contains("right.clone()"));
    }

    #[test]
    fn nth_borrows_recursive_list_but_clones_selected_element() {
        let source = r#"
#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons(A, Box<List<A>>),
}

pub fn nth<A>(x0: List<A>, n: usize) -> A
where
    A: Clone + 'static,
{
    match x0 {
        List::Cons(x, p0a) => {
            let xs = *p0a;
            if n == 0 {
                x.clone()
            } else {
                nth(xs.clone(), n - 1)
            }
        }
        _ => panic!("non-exhaustive match"),
    }
}

pub fn fetch<A>(xs: List<A>, n: usize) -> A
where
    A: Clone + 'static,
{
    nth(xs.clone(), n)
}
"#;
        let mut module = parse_rust_source(source, "Nth_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Nth_Test::nth"));
        let Item::Function(nth) = &module.items[1] else {
            panic!("expected nth function");
        };
        assert!(is_reference_type(&nth.params[0].ty));

        // Last-Use must not turn the selected `&A` into a move. The returned
        // element is still cloned, while neither recursive traversal nor the
        // caller clones the complete list.
        optimize_last_use(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn nth<A>(x0: &List<A>, n: usize) -> A"));
        assert!(printed.contains("let xs = p0a.as_ref();"));
        assert!(printed.contains("nth(xs, n - 1)"));
        assert!(printed.contains("x.clone()"));
        assert!(!printed.contains("nth(xs.clone()"));
    }

    #[test]
    fn raw_payload_move_requires_materialization_evidence() {
        let source = r#"
#[derive(Clone)]
pub struct A;

pub enum Holder<A> {
    One(A),
}

pub fn take_cloneable<A>(x: Holder<A>) -> A
where
    A: Clone + 'static,
{
    match x {
        Holder::One(value) => value,
    }
}

pub fn take_opaque<A>(x: Holder<A>) -> A {
    match x {
        Holder::One(value) => value,
    }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Test::take_cloneable"));
        assert!(!analysis.borrow_fns.contains("crate::Test::take_opaque"));

        // Last-Use runs after Borrow and must keep the clone that now
        // materializes an owned payload from a pattern-bound reference.
        optimize_last_use(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn take_cloneable<A>(x: &Holder<A>) -> A"));
        assert!(printed.contains("value.clone()"));
        assert!(printed.contains("pub fn take_opaque<A>(x: Holder<A>) -> A"));
    }

    #[test]
    fn untyped_aliases_remain_borrowed_but_typed_aliases_demand_ownership() {
        let source = r#"
pub enum Opaque {
    No,
    Yes,
}

#[derive(Clone)]
pub enum Cloneable {
    No,
    Yes,
}

pub fn inspect_opaque(x: Opaque) -> bool {
    let y = x;
    match y {
        Opaque::No => false,
        Opaque::Yes => true,
    }
}

pub fn inspect_typed(x: Cloneable) -> bool {
    let y: Cloneable = x;
    match y {
        Cloneable::No => false,
        Cloneable::Yes => true,
    }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Test::inspect_opaque"));
        assert!(!analysis.borrow_fns.contains("crate::Test::inspect_typed"));
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn inspect_opaque(x: &Opaque) -> bool"));
        assert!(printed.contains("pub fn inspect_typed(x: Cloneable) -> bool"));
        assert!(printed.contains("let y = x;"));
        assert!(!printed.contains("let y = x.clone();"));
    }

    #[test]
    fn local_builtin_names_do_not_inherit_standard_clone_facts() {
        let source = r#"
pub struct Option<A>(pub A);

pub enum Holder<A> {
    One(Option<A>),
}

pub fn take<A>(x: Holder<A>) -> Option<A>
where
    A: Clone + 'static,
{
    match x {
        Holder::One(value) => value,
    }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(!analysis.borrow_fns.contains("crate::Test::take"));
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn take<A>(x: Holder<A>) -> Option<A>"));
    }

    #[test]
    fn ordinary_box_payload_materializes_and_borrows_at_the_box_level() {
        let source = r#"
#[derive(Clone)]
pub struct Blob(pub u64);

pub enum Holder {
    One(Box<Blob>),
}

pub fn take_box(x: Holder) -> Box<Blob> {
    match x {
        Holder::One(value) => value,
    }
}

pub fn observe_box(value: &Box<Blob>) -> bool {
    true
}

pub fn forward_box(x: Holder) -> bool {
    match x {
        Holder::One(value) => observe_box(value.clone()),
    }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Test::take_box"));
        assert!(analysis.borrow_fns.contains("crate::Test::forward_box"));
        optimize_last_use(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn take_box(x: &Holder) -> Box<Blob>"));
        assert!(printed.contains("value.clone()"));
        assert!(printed.contains("observe_box(value)"));
        assert!(!printed.contains("observe_box(value.as_ref())"));
    }

    #[test]
    fn bigint_root_move_is_safe_but_still_prefers_ownership() {
        let source = r#"
use num_bigint::BigInt;

pub fn identity(x: BigInt) -> BigInt {
    x
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        let (ctx, functions) = {
            let modules = [(vec!["crate".to_string(), "Test".to_string()], &mut module)];
            BorrowContext::from_modules(&modules, &HashSet::new())
        };
        let located = functions
            .iter()
            .find(|located| located.function.name == "identity")
            .expect("identity function");
        let function = &located.function;
        let copy_generics = generic_names_with_bound(function, "Copy");
        let demands = ctx.collect_param_demands(
            function,
            &function.params[0],
            &function_type_env(function),
            &copy_generics,
            &located.scope,
        );

        assert!(demands.contains(&Demand::Move(
            MoveUse::Return(Origin::Structural, "x".to_string()),
            Materialization::Available,
        )));
        assert!(interface_borrow_safe(&demands));
        assert!(prefer_owned(&demands, true));

        let analysis = optimize_borrow(&mut module, &HashSet::new());
        assert!(!analysis.borrow_fns.contains("crate::Test::identity"));
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn identity(x: BigInt) -> BigInt"));
        assert!(!printed.contains("x.clone()"));
    }

    #[test]
    fn bclosure_keeps_materializable_raw_move_under_local_strict_gate() {
        let source = r#"
#[derive(Clone)]
pub struct Blob(pub Box<u64>);

#[derive(Clone)]
pub enum Holder {
    One(Blob),
}

pub fn run(x: Holder) -> Blob {
    ({
        let x_cap = x.clone();
        move || match x_cap {
            Holder::One(value) => value,
        }
    })()
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Test::run"));
        let Item::Function(run) = module
            .items
            .iter()
            .find(|item| matches!(item, Item::Function(function) if function.name == "run"))
            .expect("run function")
        else {
            unreachable!()
        };
        assert!(is_reference_type(&run.params[0].ty));
        let Expr::Call(callee, args) = run.body.expr.as_deref().expect("run tail") else {
            panic!("expected direct closure call");
        };
        assert!(args.is_empty());
        assert!(is_move_owncap_block(callee));

        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("let x_cap = x.clone();"));
        assert!(printed.contains("move ||"));
    }

    #[test]
    fn nth_payload_alias_does_not_create_a_second_transfer() {
        let source = r#"
#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons(A, Box<List<A>>),
}

pub fn nth_alias<A>(x0: List<A>, n: usize) -> A
where
    A: Clone + 'static,
{
    match x0 {
        List::Cons(x, p0a) => {
            let xs = *p0a;
            if n == 0 {
                let selected = x.clone();
                selected
            } else {
                nth_alias(xs.clone(), n - 1)
            }
        }
        _ => panic!("non-exhaustive match"),
    }
}
"#;
        let mut module = parse_rust_source(source, "Nth_Alias_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis
            .borrow_fns
            .contains("crate::Nth_Alias_Test::nth_alias"));
        optimize_last_use(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn nth_alias<A>(x0: &List<A>, n: usize) -> A"));
        assert!(printed.contains("let selected = x.clone();"));
        assert!(printed.contains("nth_alias(xs, n - 1)"));
    }

    #[test]
    fn recursive_subvalue_transfer_keeps_parameter_owned() {
        let source = r#"
#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons(A, Box<List<A>>),
}

pub fn take_tail<A>(x0: List<A>) -> List<A>
where
    A: Clone + 'static,
{
    match x0 {
        List::Cons(_, p0a) => {
            let xs = *p0a;
            xs.clone()
        }
        List::Nil => List::Nil,
    }
}

pub fn wrap_tail<A>(x0: List<A>) -> Option<List<A>>
where
    A: Clone + 'static,
{
    match x0 {
        List::Cons(_, p0a) => {
            let xs = *p0a;
            Some(xs.clone())
        }
        List::Nil => None,
    }
}
"#;
        let mut module = parse_rust_source(source, "Tail_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(!analysis.borrow_fns.contains("crate::Tail_Test::take_tail"));
        assert!(!analysis.borrow_fns.contains("crate::Tail_Test::wrap_tail"));
        optimize_last_use(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn take_tail<A>(x0: List<A>) -> List<A>"));
        assert!(printed.contains("pub fn wrap_tail<A>(x0: List<A>) -> Option<List<A>>"));
        assert!(printed.contains("Some(xs)"));
        assert!(!printed.contains("xs.clone()"));
    }

    #[test]
    fn wrapped_selected_payload_allows_borrowing() {
        let source = r#"
#[derive(Clone)]
pub struct Blob(pub Box<u64>);

#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons(A, Box<List<A>>),
}

pub fn first(x0: List<Blob>) -> Option<Blob> {
    match x0 {
        List::Cons(x, _) => Some(x.clone()),
        List::Nil => None,
    }
}
"#;
        let mut module = parse_rust_source(source, "Payload_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Payload_Test::first"));
        optimize_last_use(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn first(x0: &List<Blob>) -> Option<Blob>"));
        assert!(printed.contains("Some(x.clone())"));
    }

    #[test]
    fn transferring_multiple_payload_fields_keeps_parameter_owned() {
        let source = r#"
#[derive(Clone)]
pub struct Blob(pub Box<u64>);

#[derive(Clone)]
pub enum Pair {
    Both(Blob, Blob),
}

pub fn split(x0: Pair) -> (Blob, Blob) {
    match x0 {
        Pair::Both(left, right) => (left.clone(), right.clone()),
    }
}
"#;
        let mut module = parse_rust_source(source, "Pair_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(!analysis.borrow_fns.contains("crate::Pair_Test::split"));
        optimize_last_use(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn split(x0: Pair) -> (Blob, Blob)"));
        assert!(printed.contains("(left, right)"));
        assert!(!printed.contains("left.clone()"));
        assert!(!printed.contains("right.clone()"));
    }

    #[test]
    fn mutually_exclusive_payload_selection_allows_borrowing() {
        let source = r#"
#[derive(Clone)]
pub struct Blob(pub Box<u64>);

#[derive(Clone)]
pub enum Pair {
    Both(Blob, Blob),
}

pub fn choose(x0: Pair, left: bool) -> Blob {
    match x0 {
        Pair::Both(x, y) => {
            if left { x.clone() } else { y.clone() }
        }
    }
}
"#;
        let mut module = parse_rust_source(source, "Choice_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Choice_Test::choose"));
    }

    #[test]
    fn tuple_parameter_projection_is_payload_not_recursive_structure() {
        let source = r#"
#[derive(Clone)]
pub struct Blob(pub Box<u64>);

pub fn first(x0: (Blob, Blob)) -> Blob {
    match x0 {
        (x, _) => x.clone(),
    }
}
"#;
        let mut module = parse_rust_source(source, "Tuple_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Tuple_Test::first"));
    }

    #[test]
    fn derived_if_let_remains_owned_until_pattern_rewrite_is_supported() {
        let function = function(
            "is_leaf_if_let",
            "x",
            named("Tree"),
            block_tail(Expr::IfLet {
                pattern: "Tree::Leaf".to_string(),
                value: Box::new(Expr::Ident("x".to_string())),
                then_branch: block_tail(Expr::Literal(Literal::Bool(true))),
                else_branch: Some(block_tail(Expr::Literal(Literal::Bool(false)))),
            }),
        );
        let mut module = RustModule {
            name: "If_Let_Test".to_string(),
            docs: vec![],
            items: vec![tree_enum(), Item::Function(function)],
            attrs: vec![],
            vis: Visibility::Public,
        };

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(!analysis
            .borrow_fns
            .contains("crate::If_Let_Test::is_leaf_if_let"));
    }

    #[test]
    fn non_last_use_clone_still_allows_borrowing() {
        let body = Block {
            stmts: vec![Statement::Let(LetStmt {
                ifmut: false,
                name: "saved".to_string(),
                ty: None,
                init: Some(clone_call("x")),
            })],
            expr: leaf_match_body("x").expr,
        };
        let mut module = RustModule {
            name: "Test".to_string(),
            docs: vec![],
            items: vec![
                tree_enum(),
                Item::Function(function("clone_then_inspect", "x", named("Tree"), body)),
            ],
            attrs: vec![],
            vis: Visibility::Public,
        };

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis
            .borrow_fns
            .contains("crate::Test::clone_then_inspect"));
        let Item::Function(function) = &module.items[1] else {
            panic!("expected function");
        };
        assert!(is_reference_type(&function.params[0].ty));
    }

    #[test]
    fn callable_trait_container_is_not_borrow_candidate() {
        let callable = Type::Generic(
            "Rc".to_string(),
            vec![Type::CallableTrait(CallableTraitType {
                qualifier: CallableTraitQualifier::Dyn,
                trait_name: "Fn".to_string(),
                args: vec![named("Tree")],
                return_type: Box::new(named("Tree")),
            })],
        );
        let mut module = module_with(function(
            "unused_callable",
            "f",
            callable,
            block_tail(Expr::Literal(Literal::Bool(true))),
        ));

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.is_empty());
        let Item::Function(function) = &module.items[0] else {
            panic!("expected function");
        };
        assert!(!is_reference_type(&function.params[0].ty));
    }

    #[test]
    fn borrowed_tuple_match_scrutinee_does_not_clone_params() {
        let mut function = function(
            "both_leaf",
            "x",
            named("Tree"),
            tuple_leaf_match_body("x", "y"),
        );
        function.params.push(Param {
            name: "y".to_string(),
            ty: named("Tree"),
        });
        let mut module = RustModule {
            name: "Test".to_string(),
            docs: vec![],
            items: vec![tree_enum(), Item::Function(function)],
            attrs: vec![],
            vis: Visibility::Public,
        };

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Test::both_leaf"));
        let Item::Function(function) = &module.items[1] else {
            panic!("expected function");
        };
        let Some(Expr::Match { expr, .. }) = function.body.expr.as_deref() else {
            panic!("expected match tail");
        };
        assert!(matches!(
            expr.as_ref(),
            Expr::Tuple(elems)
                if matches!(&elems[0], Expr::Ident(name) if name == "x")
                    && matches!(&elems[1], Expr::Ident(name) if name == "y")
        ));
    }

    #[test]
    fn mixed_tuple_match_borrows_recursive_component_and_preserves_all_columns() {
        let source = r#"
#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons(A, Box<List<A>>),
}

pub fn nth<A>(x0: List<A>, n: usize) -> A
where
    A: Clone + 'static,
{
    match (x0, n) {
        (List::Cons(x, p0), n) => {
            let xs = *p0;
            if n == 0 {
                x.clone()
            } else {
                nth(xs.clone(), n - 1)
            }
        }
        _ => panic!("non-exhaustive match"),
    }
}
"#;
        let mut module = parse_rust_source(source, "Mixed_Tuple_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Mixed_Tuple_Test::nth"));
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn nth<A>(x0: &List<A>, n: usize) -> A"));
        assert!(printed.contains("match (x0, n)"));
        assert!(printed.contains("(List::Cons(x, p0), n)"));
        assert!(printed.contains("let xs = p0.as_ref();"));
        assert!(printed.contains("nth(xs, n - 1)"));
        assert!(!printed.contains("x0.clone()"));
    }

    #[test]
    fn mixed_tuple_match_keeps_owned_columns_before_and_after_borrowed_column() {
        let source = r#"
#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons(A, Box<List<A>>),
}

pub fn walk<A>(before: bool, xs: List<A>, after: usize) -> bool
where
    A: Clone + 'static,
{
    match (before, xs, after) {
        (false, List::Nil, 0) => false,
        (before, List::Nil, _) => before,
        (before, List::Cons(_, p0), after) => {
            let tail = *p0;
            if after == 0 {
                before
            } else {
                walk(before, tail.clone(), after - 1)
            }
        }
    }
}
"#;
        let mut module = parse_rust_source(source, "Mixed_Order_Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(analysis
            .borrow_fns
            .contains("crate::Mixed_Order_Test::walk"));
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(
            printed.contains("pub fn walk<A>(before: bool, xs: &List<A>, after: usize) -> bool")
        );
        assert!(printed.contains("match (before, xs, after)"));
        assert!(printed.contains("(false, List::Nil, 0)"));
        assert!(printed.contains("(before, List::Cons(_, p0), after)"));
        assert!(printed.contains("let tail = p0.as_ref();"));
        assert!(printed.contains("walk(before, tail, after - 1)"));
        assert!(!printed.contains("xs.clone()"));
    }

    #[test]
    fn package_borrow_summaries_rewrite_calls_across_modules() {
        let callee = function("is_leaf", "x", named("Tree"), leaf_match_body("x"));
        let mut callee_module = RustModule {
            name: "TreeMod".to_string(),
            docs: vec![],
            items: vec![tree_enum(), Item::Function(callee)],
            attrs: vec![],
            vis: Visibility::Public,
        };

        let caller = FunctionDef {
            name: "caller".to_string(),
            params: vec![Param {
                name: "x".to_string(),
                ty: named("Tree"),
            }],
            return_type: named("bool"),
            generics: vec![],
            body: block_tail(Expr::Call(
                Box::new(Expr::Ident("is_leaf".to_string())),
                vec![clone_call("x")],
            )),
            asyncness: false,
            vis: Visibility::Public,
            docs: vec![],
            attrs: vec![],
        };
        let mut caller_module = RustModule {
            name: "Test".to_string(),
            docs: vec![],
            items: vec![
                Item::Use(UseStatement {
                    path: vec![
                        "crate".to_string(),
                        "TreeMod".to_string(),
                        "is_leaf".to_string(),
                    ],
                    kind: UseKind::Simple,
                }),
                Item::Function(caller),
            ],
            attrs: vec![],
            vis: Visibility::Public,
        };
        let mut modules = vec![&mut callee_module, &mut caller_module];

        let analysis = optimize_borrow_modules(&mut modules, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::TreeMod::is_leaf"));
        let Item::Function(function) = &caller_module.items[1] else {
            panic!("expected function");
        };
        let Some(Expr::Call(_, args)) = function.body.expr.as_deref() else {
            panic!("expected call tail");
        };
        assert!(matches!(&args[0], Expr::Ident(name) if name == "x"));
    }

    #[test]
    fn package_materialization_facts_keep_same_named_types_scoped() {
        let left_source = r#"
#[derive(Clone, Copy)]
pub struct Blob(pub u64);

pub enum HolderLeft {
    LeftOne(Blob),
}

pub fn take_left(x: HolderLeft) -> Blob {
    match x { HolderLeft::LeftOne(value) => value }
}
"#;
        let right_source = r#"
pub struct Blob(pub u64);

pub enum HolderRight {
    RightOne(Blob),
}

pub fn take_right(x: HolderRight) -> Blob {
    match x { HolderRight::RightOne(value) => value }
}
"#;
        let mut left = parse_rust_source(left_source, "Left").expect("left source parses");
        let mut right = parse_rust_source(right_source, "Right").expect("right source parses");
        let mut modules = vec![&mut left, &mut right];

        let analysis = optimize_borrow_modules(&mut modules, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Left::take_left"));
        assert!(!analysis.borrow_fns.contains("crate::Right::take_right"));
    }

    #[test]
    fn package_borrow_resolves_same_named_datatypes_by_canonical_identity() {
        let wrapper_source = r#"
#[derive(Clone)]
pub enum Rbt<B, A> {
    RBT(crate::RBT_Impl::Rbt<B, A>),
}

pub fn impl_of<A, B>(x0: Rbt<B, A>) -> crate::RBT_Impl::Rbt<B, A>
where
    A: Clone + 'static,
    B: Clone + 'static,
{
    match x0 {
        Rbt::RBT(x) => x.clone(),
    }
}
"#;
        let implementation_source = r#"
#[derive(Clone, Copy)]
pub enum Color {
    R,
    B,
}

#[derive(Clone)]
pub enum Rbt<A, B> {
    Empty,
    Branch(Color, Box<Rbt<A, B>>, A, B, Box<Rbt<A, B>>),
}

pub fn is_black(x0: Color) -> bool {
    match x0 {
        Color::B => true,
        Color::R => false,
    }
}

pub fn color_of<B, A>(x0: Rbt<A, B>) -> Color
where
    A: Clone + 'static,
    B: Clone + 'static,
{
    match x0 {
        Rbt::Empty => Color::B,
        Rbt::Branch(c, _, _, _, _) => c.clone(),
    }
}

pub fn inv1<B, A>(x0: Rbt<A, B>) -> bool
where
    A: Clone + 'static,
    B: Clone + 'static,
{
    match x0 {
        Rbt::Empty => true,
        Rbt::Branch(_, left, _, _, right) => {
            let lt = *left;
            let rt = *right;
            inv1(lt.clone()) && (inv1(rt.clone()) && is_black(color_of(lt.clone())))
        }
    }
}
"#;
        let mut wrapper = parse_rust_source(wrapper_source, "RBT").expect("wrapper source parses");
        let mut implementation = parse_rust_source(implementation_source, "RBT_Impl")
            .expect("implementation source parses");
        let mut modules = vec![&mut wrapper, &mut implementation];

        let analysis = optimize_borrow_modules(&mut modules, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::RBT::impl_of"));
        assert!(analysis.borrow_fns.contains("crate::RBT_Impl::color_of"));
        assert!(analysis.borrow_fns.contains("crate::RBT_Impl::inv1"));

        let Item::Function(impl_of) = &wrapper.items[1] else {
            panic!("expected wrapper function");
        };
        let Item::Function(color_of) = &implementation.items[3] else {
            panic!("expected color_of function");
        };
        let Item::Function(inv1) = &implementation.items[4] else {
            panic!("expected inv1 function");
        };
        assert!(is_reference_type(&impl_of.params[0].ty));
        assert!(is_reference_type(&color_of.params[0].ty));
        assert!(is_reference_type(&inv1.params[0].ty));
    }

    #[test]
    fn package_borrow_resolves_renamed_imports_to_canonical_datatypes() {
        let source = r#"
#[derive(Clone, Copy)]
pub struct Payload(pub u64);

#[derive(Clone)]
pub enum Tree {
    Empty,
    Leaf(Payload),
}
"#;
        let consumer_source = r#"
use crate::Source::Tree as ImportedTree;

#[derive(Clone)]
pub enum Tree {
    Other(Box<u64>),
}

pub fn payload(x0: ImportedTree) -> Option<crate::Source::Payload> {
    match x0 {
        ImportedTree::Empty => None,
        ImportedTree::Leaf(value) => Some(value.clone()),
    }
}
"#;
        let mut source = parse_rust_source(source, "Source").expect("source module parses");
        let mut consumer =
            parse_rust_source(consumer_source, "Consumer").expect("consumer module parses");
        let mut modules = vec![&mut source, &mut consumer];

        let analysis = optimize_borrow_modules(&mut modules, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::Consumer::payload"));
        let Item::Function(payload) = &consumer.items[2] else {
            panic!("expected payload function");
        };
        assert!(is_reference_type(&payload.params[0].ty));
    }

    #[test]
    fn imported_datatype_fields_keep_their_declaration_scope() {
        let left_source = r#"
pub struct Payload(pub Box<u64>);

pub enum Holder {
    One(Payload),
}
"#;
        let right_source = r#"
use crate::Left::Holder;

#[derive(Clone)]
pub struct Payload(pub u64);

pub fn take(x: Holder) -> crate::Left::Payload {
    match x { Holder::One(value) => value }
}
"#;
        let mut left = parse_rust_source(left_source, "Left").expect("left source parses");
        let mut right = parse_rust_source(right_source, "Right").expect("right source parses");
        let mut modules = vec![&mut left, &mut right];

        let analysis = optimize_borrow_modules(&mut modules, &HashSet::new());

        assert!(!analysis.borrow_fns.contains("crate::Right::take"));
    }

    #[test]
    fn concrete_clone_impl_does_not_apply_to_other_instantiations() {
        let source = r#"
pub struct Foo<A>(pub A);

impl Clone for Foo<u8> {
    fn clone(&self) -> Self { Foo(self.0) }
}

pub enum Holder {
    One(Foo<String>),
}

pub fn take(x: Holder) -> Foo<String> {
    match x { Holder::One(value) => value }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");

        let analysis = optimize_borrow(&mut module, &HashSet::new());

        assert!(!analysis.borrow_fns.contains("crate::Test::take"));
    }

    #[test]
    fn runtime_clone_facts_require_an_external_path_root() {
        let scope = test_scope();

        assert!(known_unconditional_clone_type("num_bigint::BigInt", &scope));
        assert!(!known_unconditional_clone_type(
            "crate::wrapper::num_bigint::BigInt",
            &scope
        ));
    }

    #[test]
    fn borrowed_call_drops_clone_for_untyped_pattern_binding() {
        let callee = function("is_leaf", "x", named("Tree"), leaf_match_body("x"));
        let caller = FunctionDef {
            name: "caller".to_string(),
            params: vec![],
            return_type: named("bool"),
            generics: vec![],
            body: block_tail(Expr::Match {
                expr: Box::new(Expr::Ident("unknown_value".to_string())),
                arms: vec![MatchArm {
                    pattern: "tmp".to_string(),
                    guard: None,
                    body: block_tail(Expr::Call(
                        Box::new(Expr::Ident("is_leaf".to_string())),
                        vec![clone_call("tmp")],
                    )),
                }],
            }),
            asyncness: false,
            vis: Visibility::Public,
            docs: vec![],
            attrs: vec![],
        };
        let mut module = RustModule {
            name: "Test".to_string(),
            docs: vec![],
            items: vec![tree_enum(), Item::Function(callee), Item::Function(caller)],
            attrs: vec![],
            vis: Visibility::Public,
        };

        optimize_borrow(&mut module, &HashSet::new());

        let Item::Function(caller) = &module.items[2] else {
            panic!("expected caller");
        };
        let Some(Expr::Match { arms, .. }) = caller.body.expr.as_deref() else {
            panic!("expected match tail");
        };
        let Some(Expr::Call(_, args)) = arms[0].body.expr.as_deref() else {
            panic!("expected call in match arm");
        };
        assert!(matches!(
            &args[0],
            Expr::Reference(inner, true, false)
                if matches!(inner.as_ref(), Expr::Ident(name) if name == "tmp")
        ));
    }

    #[test]
    fn package_borrow_summaries_keep_same_named_functions_distinct() {
        let borrow_probe = function("probe", "x", named("Tree"), leaf_match_body("x"));
        let mut borrow_module = RustModule {
            name: "BorrowMod".to_string(),
            docs: vec![],
            items: vec![tree_enum(), Item::Function(borrow_probe)],
            attrs: vec![],
            vis: Visibility::Public,
        };

        let own_probe = FunctionDef {
            name: "probe".to_string(),
            params: vec![Param {
                name: "x".to_string(),
                ty: named("Tree"),
            }],
            return_type: named("Tree"),
            generics: vec![],
            body: block_tail(Expr::Ident("x".to_string())),
            asyncness: false,
            vis: Visibility::Public,
            docs: vec![],
            attrs: vec![],
        };
        let mut own_module = RustModule {
            name: "OwnMod".to_string(),
            docs: vec![],
            items: vec![Item::Function(own_probe)],
            attrs: vec![],
            vis: Visibility::Public,
        };

        let qualified_call = |module: &str, arg: Expr| {
            Expr::Call(
                Box::new(Expr::Path(
                    vec!["crate".to_string(), module.to_string(), "probe".to_string()],
                    PathType::Namespace,
                )),
                vec![arg],
            )
        };
        let caller = FunctionDef {
            name: "caller".to_string(),
            params: vec![
                Param {
                    name: "x".to_string(),
                    ty: named("Tree"),
                },
                Param {
                    name: "y".to_string(),
                    ty: named("Tree"),
                },
            ],
            return_type: Type::Tuple(vec![named("bool"), named("Tree")]),
            generics: vec![],
            body: block_tail(Expr::Tuple(vec![
                qualified_call("BorrowMod", clone_call("x")),
                qualified_call("OwnMod", clone_call("y")),
            ])),
            asyncness: false,
            vis: Visibility::Public,
            docs: vec![],
            attrs: vec![],
        };
        let mut caller_module = module_with(caller);
        let mut modules = vec![&mut borrow_module, &mut own_module, &mut caller_module];

        let analysis = optimize_borrow_modules(&mut modules, &HashSet::new());

        assert!(analysis.borrow_fns.contains("crate::BorrowMod::probe"));
        assert!(!analysis.borrow_fns.contains("crate::OwnMod::probe"));

        let Item::Function(borrow_probe) = &borrow_module.items[1] else {
            panic!("expected borrow probe");
        };
        assert!(is_reference_type(&borrow_probe.params[0].ty));
        let Item::Function(own_probe) = &own_module.items[0] else {
            panic!("expected owned probe");
        };
        assert!(!is_reference_type(&own_probe.params[0].ty));

        let Item::Function(caller) = &caller_module.items[0] else {
            panic!("expected caller");
        };
        let Some(Expr::Tuple(calls)) = caller.body.expr.as_deref() else {
            panic!("expected tuple of calls");
        };
        let Expr::Call(_, borrow_args) = &calls[0] else {
            panic!("expected borrowed call");
        };
        let Expr::Call(_, own_args) = &calls[1] else {
            panic!("expected owned call");
        };
        assert!(matches!(&borrow_args[0], Expr::Ident(name) if name == "x"));
        assert!(matches!(
            &own_args[0],
            Expr::MethodCall(receiver, method, args)
                if matches!(receiver.as_ref(), Expr::Ident(name) if name == "y")
                    && method == "clone"
                    && args.is_empty()
        ));
    }

    #[test]
    fn turbofish_callee_uses_borrow_summary() {
        let callee = function("conv", "x", named("Tree"), leaf_match_body("x"));
        let mut callee_module = RustModule {
            name: "TreeMod".to_string(),
            docs: vec![],
            items: vec![tree_enum(), Item::Function(callee)],
            attrs: vec![],
            vis: Visibility::Public,
        };

        let caller = FunctionDef {
            name: "caller".to_string(),
            params: vec![Param {
                name: "x".to_string(),
                ty: named("Tree"),
            }],
            return_type: named("bool"),
            generics: vec![],
            body: block_tail(Expr::Call(
                Box::new(Expr::Path(
                    vec![
                        "crate".to_string(),
                        "TreeMod".to_string(),
                        "conv::<A>".to_string(),
                    ],
                    PathType::Namespace,
                )),
                vec![clone_call("x")],
            )),
            asyncness: false,
            vis: Visibility::Public,
            docs: vec![],
            attrs: vec![],
        };
        let mut caller_module = module_with(caller);
        let mut modules = vec![&mut callee_module, &mut caller_module];

        optimize_borrow_modules(&mut modules, &HashSet::new());

        let Item::Function(function) = &caller_module.items[0] else {
            panic!("expected function");
        };
        let Some(Expr::Call(_, args)) = function.body.expr.as_deref() else {
            panic!("expected call tail");
        };
        assert!(matches!(&args[0], Expr::Ident(name) if name == "x"));
    }

    #[test]
    fn impl_method_body_uses_borrow_summary_without_signature_rewrite() {
        let callee = function("is_leaf", "x", named("Tree"), leaf_match_body("x"));
        let method = FunctionDef {
            name: "equal".to_string(),
            params: vec![Param {
                name: "x".to_string(),
                ty: named("Tree"),
            }],
            return_type: named("bool"),
            generics: vec![],
            body: block_tail(Expr::Call(
                Box::new(Expr::Ident("is_leaf".to_string())),
                vec![clone_call("x")],
            )),
            asyncness: false,
            vis: Visibility::Private,
            docs: vec![],
            attrs: vec![],
        };
        let mut module = RustModule {
            name: "Test".to_string(),
            docs: vec![],
            items: vec![
                tree_enum(),
                Item::Function(callee),
                Item::Impl(ImplBlock {
                    target: named("Tree"),
                    generics: vec![],
                    items: vec![ImplItem::Method(method)],
                    trait_impl: None,
                }),
            ],
            attrs: vec![],
            vis: Visibility::Public,
        };

        optimize_borrow(&mut module, &HashSet::new());

        let Item::Impl(impl_block) = &module.items[2] else {
            panic!("expected impl");
        };
        let ImplItem::Method(method) = &impl_block.items[0] else {
            panic!("expected method");
        };
        assert!(!is_reference_type(&method.params[0].ty));
        let Some(Expr::Call(_, args)) = method.body.expr.as_deref() else {
            panic!("expected call tail");
        };
        assert!(matches!(
            &args[0],
            Expr::Reference(inner, true, false)
                if matches!(inner.as_ref(), Expr::Ident(name) if name == "x")
        ));
    }

    #[test]
    fn bclosure_rewrites_direct_local_call() {
        let block = block_with_closure_binding(Expr::Call(
            Box::new(Expr::Ident("f".to_string())),
            vec![lit_i(0)],
        ));

        let rewritten = rewrite_test_block(&block);

        assert!(matches!(
            first_let_init(&rewritten),
            Expr::Closure(_, _, false)
        ));
    }

    #[test]
    fn bclosure_keeps_move_when_returned_as_component() {
        let block =
            block_with_closure_binding(Expr::Tuple(vec![Expr::Ident("f".to_string()), lit_i(0)]));

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

    #[test]
    fn escaping_copy_capture_materializes_borrowed_value() {
        let block = Block {
            stmts: vec![Statement::Let(LetStmt {
                ifmut: false,
                name: "y_cap".to_string(),
                ty: None,
                init: Some(Expr::Ident("y".to_string())),
            })],
            expr: Some(Box::new(Expr::Closure(
                vec![ClosureParam::typed("x", named("i32"))],
                Box::new(Expr::Ident("y_cap".to_string())),
                true,
            ))),
        };
        let ctx = empty_ctx();
        let orig_env = HashMap::from([("y".to_string(), named("i32"))]);
        let mut borrow_env = HashMap::from([("y".to_string(), make_ref_type(&named("i32")))]);

        let rewritten = ctx.rewrite_block_borrow(
            &block,
            &mut borrow_env,
            &orig_env,
            &HashSet::new(),
            &test_scope(),
        );

        let Statement::Let(capture) = &rewritten.stmts[0] else {
            panic!("expected capture binding");
        };
        assert!(matches!(
            capture.init.as_ref(),
            Some(Expr::UnaryOp(op, inner))
                if op == "*"
                    && matches!(inner.as_ref(), Expr::Ident(name) if name == "y")
        ));
        assert!(matches!(
            rewritten.expr.as_deref(),
            Some(Expr::Closure(_, _, true))
        ));
    }

    #[test]
    fn bcall_rewrites_top_level_calls_inside_closure_body() {
        let mut ctx = empty_ctx();
        let make_triple_id = vec![
            "crate".to_string(),
            "Test".to_string(),
            "make_triple".to_string(),
        ];
        ctx.borrow_positions
            .insert(make_triple_id.clone(), vec![0, 1, 2]);
        ctx.fn_sigs.insert(
            make_triple_id,
            (
                vec![],
                vec![named("bool"), named("bool"), named("bool")],
                named("bool"),
            ),
        );

        let borrow_env = HashMap::from([
            ("x_cap".to_string(), named("bool")),
            ("a".to_string(), make_ref_type(&named("bool"))),
        ]);
        let orig_env = borrow_env.clone();
        let expr = Expr::Closure(
            vec![
                ClosureParam::typed("a", named("bool")),
                ClosureParam::typed("b", named("bool")),
            ],
            Box::new(Expr::Call(
                Box::new(Expr::Ident("make_triple".to_string())),
                vec![clone_call("x_cap"), clone_call("a"), clone_call("b")],
            )),
            true,
        );

        let rewritten = ctx.rewrite_expr_own(
            &expr,
            &borrow_env,
            &orig_env,
            &HashSet::new(),
            &test_scope(),
        );

        let Expr::Closure(_, body, true) = rewritten else {
            panic!("expected rewritten move closure");
        };
        let Expr::Call(_, args) = body.as_ref() else {
            panic!("expected call in closure body");
        };
        assert_eq!(args.len(), 3);
        assert!(args
            .iter()
            .all(|arg| matches!(arg, Expr::Reference(_, true, false))));
    }

    #[test]
    fn size_aware_policy_keeps_small_copy_values_owned() {
        let source = r#"
#[derive(Clone, Copy)]
pub enum Small { No, Yes }

pub fn observe(x: Small) -> bool {
    match x { Small::No => false, Small::Yes => true }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        let inferred_copy_types = optimize_copy(&mut module).inferred_copy_types;
        optimize_borrow(&mut module, &inferred_copy_types);

        let Item::Function(observe) = module
            .items
            .iter()
            .find(|item| matches!(item, Item::Function(function) if function.name == "observe"))
            .expect("observe function")
        else {
            unreachable!()
        };
        assert!(!is_reference_type(&observe.params[0].ty));
    }

    #[test]
    fn copy_ablation_retains_source_copy_facts_for_borrow() {
        let source = r#"
#[derive(Clone, Copy)]
pub enum Small { No, Yes }

pub fn observe(x: Small) -> bool {
    match x { Small::No => false, Small::Yes => true }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");

        // This is the downstream state used by --disable-copy: no inferred
        // facts are passed in, but the source derive remains valid.
        optimize_borrow(&mut module, &HashSet::new());

        let Item::Function(observe) = module
            .items
            .iter()
            .find(|item| matches!(item, Item::Function(function) if function.name == "observe"))
            .expect("observe function")
        else {
            unreachable!()
        };
        assert!(!is_reference_type(&observe.params[0].ty));
    }

    #[test]
    fn copy_ablation_does_not_reconstruct_an_inferred_copy_fact() {
        let source = r#"
#[derive(Clone)]
pub enum Small { No, Yes }

pub fn observe(x: Small) -> bool {
    match x { Small::No => false, Small::Yes => true }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");

        optimize_borrow(&mut module, &HashSet::new());

        let Item::Function(observe) = module
            .items
            .iter()
            .find(|item| matches!(item, Item::Function(function) if function.name == "observe"))
            .expect("observe function")
        else {
            unreachable!()
        };
        assert!(is_reference_type(&observe.params[0].ty));
    }

    #[test]
    fn size_aware_policy_borrows_large_copy_values() {
        let source = r#"
#[derive(Clone, Copy)]
pub struct Large(pub u64, pub u64, pub u64, pub u64);

pub fn first(x: Large) -> u64 {
    match x { Large(a, _, _, _) => a }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        optimize_borrow(&mut module, &HashSet::new());

        let Item::Function(first) = module
            .items
            .iter()
            .find(|item| matches!(item, Item::Function(function) if function.name == "first"))
            .expect("first function")
        else {
            unreachable!()
        };
        assert!(is_reference_type(&first.params[0].ty));
    }

    #[test]
    fn size_aware_match_borrows_medium_copy_scrutinee() {
        let source = r#"
#[derive(Clone, Copy)]
pub enum Medium { Empty, Value(u128) }

pub fn present(x: Medium) -> bool {
    match x { Medium::Empty => false, Medium::Value(_) => true }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        optimize_borrow(&mut module, &HashSet::new());

        let Item::Function(present) = module
            .items
            .iter()
            .find(|item| matches!(item, Item::Function(function) if function.name == "present"))
            .expect("present function")
        else {
            unreachable!()
        };
        assert!(is_reference_type(&present.params[0].ty));

        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("match x"));
        assert!(!printed.contains("match *x"));
    }

    #[test]
    fn front_copy_removes_large_match_clone_before_borrow() {
        let source = r#"
#[derive(Clone)]
pub enum Large { Empty, Value([u128; 3]) }

pub fn keep(x: Large) -> Large {
    let _present = match x.clone() {
        Large::Empty => false,
        Large::Value(_) => true,
    };
    x
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        let inferred_copy_types = optimize_copy(&mut module).inferred_copy_types;

        let mut generator = RustCodeGenerator::new();
        let after_copy = generator.generate_module_code(&module);
        assert!(after_copy.contains("match x"));
        assert!(!after_copy.contains("match x.clone()"));

        optimize_borrow(&mut module, &inferred_copy_types);

        let Item::Function(keep) = module
            .items
            .iter()
            .find(|item| matches!(item, Item::Function(function) if function.name == "keep"))
            .expect("keep function")
        else {
            unreachable!()
        };
        assert!(is_reference_type(&keep.params[0].ty));

        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("match x"));
        assert!(!printed.contains("match x.clone()"));
    }

    #[test]
    fn typed_closure_match_uses_the_closure_parameter_type() {
        let source = r#"
#[derive(Clone)]
pub enum Small { First, Second }

pub fn keep(x: Small) -> Small {
    (move |y: Small| {
        match y.clone() {
            Small::First => y,
            Small::Second => y,
        }
    })(x)
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        let inferred_copy_types = optimize_copy(&mut module).inferred_copy_types;
        optimize_borrow(&mut module, &inferred_copy_types);

        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("match y"));
        assert!(!printed.contains("match y.clone()"));
    }

    #[test]
    fn local_match_borrows_a_cloned_scrutinee_while_preserving_final_move() {
        let source = r#"
#[derive(Clone)]
pub enum State {
    Ready(bool, Box<bool>),
    Halted,
}

pub fn keep(x: State) -> State {
    let _seen = match x.clone() {
        State::Ready(flag, _) => flag,
        State::Halted => false,
    };
    x
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        optimize_borrow(&mut module, &HashSet::new());

        let Item::Function(keep) = module
            .items
            .iter()
            .find(|item| matches!(item, Item::Function(function) if function.name == "keep"))
            .expect("keep function")
        else {
            unreachable!()
        };
        assert!(!is_reference_type(&keep.params[0].ty));

        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("match &x"));
        assert!(!printed.contains("match x.clone()"));
    }

    #[test]
    fn local_match_borrows_a_direct_scrutinee_while_preserving_later_owner_move() {
        let source = r#"
#[derive(Clone)]
pub enum State {
    Ready(bool, Box<bool>),
    Halted,
}

pub fn keep(x: State) -> State {
    let _seen = match x {
        State::Ready(flag, _) => flag,
        State::Halted => false,
    };
    x
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        optimize_borrow(&mut module, &HashSet::new());

        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn keep(x: State) -> State"));
        assert!(printed.contains("match &x"));
        assert!(printed.contains("State::Ready(flag, _) =>"));
        assert!(printed.contains("*flag"));
    }

    #[test]
    fn local_matches_over_one_owner_make_independent_prefer_owned_decisions() {
        let source = r#"
#[derive(Clone)]
pub struct Blob(pub Box<u64>);

#[derive(Clone)]
pub enum Outcome {
    Stuck,
    Next(Blob, Blob),
}

pub fn consume(left: Blob, right: Blob) -> Outcome {
    Outcome::Next(left, right)
}

pub fn step(st: Outcome) -> Outcome {
    let _seen = match st.clone() {
        Outcome::Stuck => true,
        Outcome::Next(_, _) => false,
    };
    match st.clone() {
        Outcome::Stuck => Outcome::Stuck,
        Outcome::Next(left, right) => consume(left.clone(), right.clone()),
    }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        optimize_borrow(&mut module, &HashSet::new());
        optimize_last_use(&mut module);

        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("pub fn step(st: Outcome) -> Outcome"));
        assert!(printed.contains("match &st"));
        assert!(printed.contains("match st"));
        assert!(printed.contains("consume(left, right)"));
        assert!(!printed.contains("st.clone()"));
        assert!(!printed.contains("left.clone()"));
        assert!(!printed.contains("right.clone()"));
    }

    #[test]
    fn local_match_materializes_one_cloneable_payload_from_a_borrow() {
        let source = r#"
#[derive(Clone)]
pub struct Blob(pub Box<u64>);

pub enum Holder {
    One(Blob),
}

pub fn take_local() -> Blob {
    let holder = Holder::One(Blob(Box::new(0)));
    match holder {
        Holder::One(value) => value,
    }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        optimize_borrow(&mut module, &HashSet::new());

        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("match &holder"));
        assert!(printed.contains("value.clone()"));
    }

    #[test]
    fn local_match_keeps_owned_decomposition_without_materialization_evidence() {
        let source = r#"
pub struct Opaque;

pub enum Holder {
    One(Opaque),
}

pub fn take_local() -> Opaque {
    let holder = Holder::One(Opaque);
    match holder {
        Holder::One(value) => value,
    }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        optimize_borrow(&mut module, &HashSet::new());

        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("match holder"));
        assert!(!printed.contains("match &holder"));
        assert!(!printed.contains("value.clone()"));
    }

    #[test]
    fn local_match_uses_an_inferred_match_result_type() {
        let source = r#"
#[derive(Clone, Copy)]
pub enum Val {
    Undef,
    Long(u128),
}

pub enum MaybeBool {
    None,
    Some(bool),
}

pub fn eval() -> MaybeBool {
    MaybeBool::None
}

pub fn test() -> Val {
    let value = match eval() {
        MaybeBool::None => Val::Undef,
        MaybeBool::Some(true) => Val::Long(1u128),
        MaybeBool::Some(false) => Val::Long(0u128),
    };
    match value.clone() {
        Val::Undef => Val::Undef,
        Val::Long(word) => Val::Long(word.clone()),
    }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        let copy = crate::copy_analysis::optimize_copy(&mut module);
        optimize_borrow(&mut module, &copy.inferred_copy_types);

        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(!printed.contains("value.clone()"), "{printed}");
        assert!(!printed.contains("word.clone()"), "{printed}");
    }

    #[test]
    fn field_sensitive_match_clones_only_the_selected_field() {
        let source = r#"
#[derive(Clone)]
pub struct Blob(pub Box<u64>);

#[derive(Clone)]
pub enum Outer {
    Empty,
    Pair(Blob, Blob),
}

pub fn select_first(x: Outer) -> Blob {
    match x.clone() {
        Outer::Empty => Blob(Box::new(0)),
        Outer::Pair(first, _) => first.clone(),
    }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        optimize_borrow(&mut module, &HashSet::new());

        let Item::Function(select_first) = module
            .items
            .iter()
            .find(
                |item| matches!(item, Item::Function(function) if function.name == "select_first"),
            )
            .expect("select_first function")
        else {
            unreachable!()
        };
        assert!(is_reference_type(&select_first.params[0].ty));

        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("match x"));
        assert!(!printed.contains("match x.clone()"));
        assert!(printed.contains("first.clone()"));
    }

    #[test]
    fn borrowed_explicit_copy_value_uses_deref_instead_of_clone() {
        let source = r#"
pub struct Marker(pub Box<bool>);

pub struct Word<W>(pub u64, pub std::marker::PhantomData<W>);

impl<W> Copy for Word<W> {}

impl<W> Clone for Word<W> {
    fn clone(&self) -> Self { *self }
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");
        let modules = vec![(vec!["crate".to_string(), "Test".to_string()], &mut module)];
        let (ctx, _) = BorrowContext::from_modules(&modules, &HashSet::new());
        assert!(ctx.unconditional_copy_types.contains("Word"));

        let word_ty = Type::Generic("crate::Test::Word".to_string(), vec![named("Marker")]);
        let shared = Type::Reference(Box::new(named("bool")), true, false);
        let mutable = Type::Reference(Box::new(named("bool")), true, true);
        assert!(ctx.is_copy(&shared, &HashSet::new(), &test_scope()));
        assert!(ctx.is_materialized_copy(&shared, &HashSet::new(), &test_scope()));
        assert!(!ctx.is_copy(&mutable, &HashSet::new(), &test_scope()));
        assert!(!ctx.is_materialized_copy(&mutable, &HashSet::new(), &test_scope()));
        let borrow_env = HashMap::from([("word".to_string(), make_ref_type(&word_ty))]);
        let rewritten = ctx.rewrite_expr_own(
            &clone_call("word"),
            &borrow_env,
            &HashMap::new(),
            &HashSet::new(),
            &test_scope(),
        );
        assert!(matches!(
            rewritten,
            Expr::UnaryOp(op, inner)
                if op == "*" && matches!(inner.as_ref(), Expr::Ident(name) if name == "word")
        ));
    }
}
