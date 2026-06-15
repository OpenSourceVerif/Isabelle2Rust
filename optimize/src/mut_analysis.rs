use std::collections::{HashMap, HashSet};

use rustlightast::*;

/// Result of the mutability-inference pass.
#[derive(Debug, Clone, Default)]
pub struct MutAnalysis {
    /// Names of functions in which at least one mut chain was collapsed.
    pub mut_fns: HashSet<String>,
}

/// Collapse clone-based "mut chains" into a single `let mut` binding updated by
/// assignment, and remove the clones that become last-use moves as a result.
///
/// This is the third optimization pass (after copy and borrow).  It implements
/// the three rewrite rules from the paper:
///
///   * **M-Shadow** recovers the shadowed source name: the generated chain
///     `let x0 = s0; let x1 = s1; …; let xn = sn` (where each `s_{i+1}` reads
///     `x_i` exactly once — the *handoff* and *single-use* conditions) is the
///     same logical variable, so all the `x_i` are unified to one name.
///   * **M-Mut** turns the unified chain into `let mut x = s0; x = s1; …; x = sn`
///     under the side condition `NoEsc(x)` (no borrow of the previous value of
///     `x` outlives the assignment).
///   * **M-LastUse** rewrites `v.clone()` to `v` wherever `v` is at its last
///     use, which removes the handoff clones the mut rewrite exposes (and any
///     other already-dead clone receiver).
///
/// The pass acts purely on the ownership structure of the binding chain; the
/// right-hand sides are left untouched.
pub fn optimize_mut(module: &mut RustModule) -> MutAnalysis {
    let mut analysis = MutAnalysis::default();
    optimize_module(module, &mut analysis);
    analysis
}

type TypeEnv = HashMap<String, Type>;

/// Module-local information used to infer the type of a chain element so the
/// pass can require every element of a chain to share one owned type.
struct MutContext {
    /// `fn name → return type` (top-level functions and impl methods).
    fn_returns: HashMap<String, Type>,
    /// `variant name → owning enum` (`None` if the variant name is ambiguous).
    variant_owners: HashMap<String, Option<String>>,
}

fn optimize_module(module: &mut RustModule, analysis: &mut MutAnalysis) {
    let ctx = MutContext::from_items(&module.items);
    for item in &mut module.items {
        match item {
            Item::Function(function) => {
                if transform_function(&ctx, function) {
                    analysis.mut_fns.insert(function.name.clone());
                }
            }
            Item::Impl(impl_block) => {
                for impl_item in &mut impl_block.items {
                    if let ImplItem::Method(method) = impl_item {
                        if transform_function(&ctx, method) {
                            analysis.mut_fns.insert(method.name.clone());
                        }
                    }
                }
            }
            Item::Mod(inner) => optimize_module(inner, analysis),
            _ => {}
        }
    }
}

impl MutContext {
    fn from_items(items: &[Item]) -> Self {
        let mut fn_returns = HashMap::new();
        let mut variant_owners: HashMap<String, Option<String>> = HashMap::new();

        for item in items {
            match item {
                Item::Function(function) => {
                    fn_returns.insert(function.name.clone(), function.return_type.clone());
                }
                Item::Impl(impl_block) => {
                    for impl_item in &impl_block.items {
                        if let ImplItem::Method(method) = impl_item {
                            fn_returns.insert(method.name.clone(), method.return_type.clone());
                        }
                    }
                }
                Item::Enum(def) => {
                    for variant in &def.variants {
                        variant_owners
                            .entry(variant.name.clone())
                            .and_modify(|existing| {
                                if existing.as_deref() != Some(def.name.as_str()) {
                                    *existing = None;
                                }
                            })
                            .or_insert_with(|| Some(def.name.clone()));
                    }
                }
                _ => {}
            }
        }

        Self {
            fn_returns,
            variant_owners,
        }
    }

    /// Infer the type of `expr` under `env`, returning `None` when the shape is
    /// outside the small fragment we model.  Only used to compare chain-element
    /// types, so a `None` simply means "do not collapse this chain".
    fn infer_type(&self, expr: &Expr, env: &TypeEnv) -> Option<Type> {
        match expr {
            Expr::Ident(name) => env.get(name).cloned(),
            Expr::Path(path, PathType::Namespace) => self
                .owner_for_variant_path(path)
                .map(Type::Named)
                .or_else(|| path.last().and_then(|n| self.fn_returns.get(n).cloned())),
            Expr::Literal(Literal::Bool(_)) => Some(Type::Named("bool".to_string())),
            Expr::Call(callee, _) => self.infer_call_type(callee),
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                // `v.clone()` where `v: &T` yields an owned `T`.
                self.infer_type(receiver, env).map(strip_ref)
            }
            Expr::Reference(inner, true, mutable) => self
                .infer_type(inner, env)
                .map(|ty| Type::Reference(Box::new(ty), true, *mutable)),
            Expr::Parenthesized(inner) => self.infer_type(inner, env),
            // `*r` dereferences one reference layer; other unary ops keep the type.
            Expr::UnaryOp(op, inner) if op == "*" => self.infer_type(inner, env).map(strip_ref),
            Expr::UnaryOp(_, inner) => self.infer_type(inner, env),
            Expr::BinaryOp(left, op, right) => {
                if binop_returns_bool(op) {
                    Some(Type::Named("bool".to_string()))
                } else {
                    self.infer_type(left, env)
                        .or_else(|| self.infer_type(right, env))
                }
            }
            Expr::Tuple(items) => {
                let types: Option<Vec<_>> =
                    items.iter().map(|item| self.infer_type(item, env)).collect();
                types.map(|types| {
                    if types.is_empty() {
                        Type::Unit
                    } else {
                        Type::Tuple(types)
                    }
                })
            }
            Expr::Block(block) => block.expr.as_ref().and_then(|e| self.infer_type(e, env)),
            _ => None,
        }
    }

    fn infer_call_type(&self, callee: &Expr) -> Option<Type> {
        match callee {
            Expr::Ident(name) => self
                .owner_for_variant(name)
                .map(Type::Named)
                .or_else(|| self.fn_returns.get(name).cloned()),
            Expr::Path(path, PathType::Namespace) => self
                .owner_for_variant_path(path)
                .map(Type::Named)
                .or_else(|| path.last().and_then(|n| self.fn_returns.get(n).cloned())),
            Expr::Parenthesized(inner) => self.infer_call_type(inner),
            _ => None,
        }
    }

    fn owner_for_variant(&self, name: &str) -> Option<String> {
        self.variant_owners.get(name).cloned().flatten()
    }

    fn owner_for_variant_path(&self, path: &[String]) -> Option<String> {
        self.owner_for_variant(path.last()?)
    }
}

/// Run the chain transform and last-use elimination over a single function.
/// Returns `true` if a mut chain was collapsed.
fn transform_function(ctx: &MutContext, function: &mut FunctionDef) -> bool {
    // M-Shadow + M-Mut: collapse every chain in the body (recursing into nested
    // blocks).  This leaves the handoff clones in place; they are removed next.
    let env = function_param_env(function);
    let collapsed = transform_block(ctx, &mut function.body, &env);

    // M-LastUse: a global backward-liveness pass that turns `v.clone()` into `v`
    // when `v` is owned and not read afterwards.  Running it unconditionally is
    // sound, but it is only useful (and only changes anything) where clones are
    // genuinely dead — most importantly the handoff clones the mut rewrite just
    // exposed.
    let owned = compute_owned(function);
    let mut live: HashSet<String> = HashSet::new();
    rewrite_lastuse_block(&mut function.body, &mut live, &owned);

    if collapsed {
        ensure_function_comment(function, "// mut-optimized by in-place updates");
    }
    collapsed
}

// ── M-Shadow + M-Mut: mut-chain detection and rewrite ────────────────────────

/// Detect and rewrite every mut chain reachable from `block`, recursing into
/// nested blocks first.  `outer_env` carries the variable types in scope on
/// entry to the block.  Returns `true` if any chain was collapsed.
fn transform_block(ctx: &MutContext, block: &mut Block, outer_env: &TypeEnv) -> bool {
    let mut changed = false;
    let mut env = outer_env.clone();
    // Type of each statement's binding (by statement index), used to require
    // chain elements to share one owned type.
    let mut elem_types: HashMap<usize, Type> = HashMap::new();

    // Recurse into nested blocks (inside match arms, if/else, sub-blocks, …),
    // building up the local type environment as we go.  The Isabelle code
    // generator wraps function bodies in an inner block, so the actual chain
    // usually lives one level down.
    for idx in 0..block.stmts.len() {
        match &mut block.stmts[idx] {
            Statement::Let(let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    changed |= transform_expr(ctx, init, &env);
                }
                let inferred = let_stmt.ty.clone().or_else(|| {
                    let_stmt
                        .init
                        .as_ref()
                        .and_then(|init| ctx.infer_type(init, &env))
                });
                if is_binding_ident(&let_stmt.name) {
                    if let Some(ty) = inferred {
                        elem_types.insert(idx, ty.clone());
                        env.insert(let_stmt.name.clone(), ty);
                    }
                }
            }
            Statement::Expr(expr) => changed |= transform_expr(ctx, expr, &env),
            Statement::Item(item) => {
                if let Item::Function(function) = item.as_mut() {
                    let fn_env = function_param_env(function);
                    changed |= transform_block(ctx, &mut function.body, &fn_env);
                }
            }
            _ => {}
        }
    }
    if let Some(tail) = &mut block.expr {
        changed |= transform_expr(ctx, tail, &env);
    }

    // Now collapse chains whose `let` bindings are direct statements of *this*
    // block (so they can be turned into assignments in place).
    changed |= collapse_chains_in_block(block, &elem_types);
    changed
}

fn transform_expr(ctx: &MutContext, expr: &mut Expr, env: &TypeEnv) -> bool {
    let mut changed = false;
    match expr {
        Expr::Block(block) => changed |= transform_block(ctx, block, env),
        Expr::Loop(block) | Expr::Unsafe(block) => changed |= transform_block(ctx, block, env),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            changed |= transform_expr(ctx, condition, env);
            changed |= transform_block(ctx, then_branch, env);
            if let Some(else_branch) = else_branch {
                changed |= transform_block(ctx, else_branch, env);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            changed |= transform_expr(ctx, value, env);
            changed |= transform_block(ctx, then_branch, env);
            if let Some(else_branch) = else_branch {
                changed |= transform_block(ctx, else_branch, env);
            }
        }
        Expr::Match { expr, arms } => {
            changed |= transform_expr(ctx, expr, env);
            for arm in arms {
                if let Some(guard) = &mut arm.guard {
                    changed |= transform_expr(ctx, guard, env);
                }
                changed |= transform_block(ctx, &mut arm.body, env);
            }
        }
        Expr::Call(callee, args) => {
            changed |= transform_expr(ctx, callee, env);
            for arg in args {
                changed |= transform_expr(ctx, arg, env);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            changed |= transform_expr(ctx, receiver, env);
            for arg in args {
                changed |= transform_expr(ctx, arg, env);
            }
        }
        Expr::Tuple(items) => {
            for item in items {
                changed |= transform_expr(ctx, item, env);
            }
        }
        Expr::BinaryOp(left, _, right) | Expr::Assign(left, right) | Expr::Index(left, right) => {
            changed |= transform_expr(ctx, left, env);
            changed |= transform_expr(ctx, right, env);
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => {
            changed |= transform_expr(ctx, inner, env);
        }
        Expr::Closure(_, body, _) => changed |= transform_expr(ctx, body, env),
        Expr::Ident(_) | Expr::Path(_, _) | Expr::Literal(_) | Expr::BuilderChain(_) => {}
    }
    changed
}

/// Find every mut chain among the direct `let` statements of `block` and rewrite
/// it to the `let mut` + assignment form.
fn collapse_chains_in_block(block: &mut Block, elem_types: &HashMap<usize, Type>) -> bool {
    let chains = detect_chains(block, elem_types);
    if chains.is_empty() {
        return false;
    }

    // Combine all chains into one rewrite plan.  Each chain unifies its
    // generated names `x0, x1, …, xn` to `x0` (the first, already-unique name).
    let mut rename_map: HashMap<String, String> = HashMap::new();
    let mut mut_starts: HashSet<usize> = HashSet::new();
    let mut assign_targets: HashMap<usize, String> = HashMap::new();

    for chain in &chains {
        let mut_name = let_binding_name(&block.stmts[chain[0]])
            .expect("chain head is a simple let")
            .to_string();
        mut_starts.insert(chain[0]);
        for &idx in &chain[1..] {
            let name = let_binding_name(&block.stmts[idx])
                .expect("chain element is a simple let")
                .to_string();
            rename_map.insert(name, mut_name.clone());
            assign_targets.insert(idx, mut_name.clone());
        }
    }

    // M-Shadow: rename every *read* of a unified name to the chosen name.  This
    // covers both the handoff uses (in the next element's rhs) and the later
    // uses of the final element in the continuation.
    if !rename_map.is_empty() {
        rename_reads_block(block, &rename_map);
    }

    // M-Mut: the first element becomes `let mut x = s0`; the rest become
    // assignments `x = si`.
    let old_stmts = std::mem::take(&mut block.stmts);
    let mut new_stmts = Vec::with_capacity(old_stmts.len());
    for (idx, stmt) in old_stmts.into_iter().enumerate() {
        if mut_starts.contains(&idx) {
            if let Statement::Let(mut let_stmt) = stmt {
                let_stmt.ifmut = true;
                new_stmts.push(Statement::Let(let_stmt));
            }
        } else if let Some(mut_name) = assign_targets.get(&idx) {
            if let Statement::Let(let_stmt) = stmt {
                let init = let_stmt
                    .init
                    .expect("chain element always has an initialiser");
                new_stmts.push(Statement::Expr(Expr::Assign(
                    Box::new(Expr::Ident(mut_name.clone())),
                    Box::new(init),
                )));
            }
        } else {
            new_stmts.push(stmt);
        }
    }
    block.stmts = new_stmts;

    true
}

/// Detect all mut chains whose bindings are direct statements of `block`.
/// Each returned chain is the ordered list of statement indices `x0, …, xn`
/// (with `n >= 1`, i.e. at least one shadowing binding).
fn detect_chains(block: &Block, elem_types: &HashMap<usize, Type>) -> Vec<Vec<usize>> {
    // Statement indices that are `let <ident> = <init>;` bindings.
    let candidate_lets: Vec<usize> = block
        .stmts
        .iter()
        .enumerate()
        .filter(|(_, stmt)| is_simple_let_with_init(stmt))
        .map(|(idx, _)| idx)
        .collect();

    let mut chains = Vec::new();
    let mut consumed: HashSet<usize> = HashSet::new();

    for &start in &candidate_lets {
        if consumed.contains(&start) {
            continue;
        }

        // A chain can only be anchored on an element whose owned type we know,
        // so the type-equality check below is meaningful.
        let Some(start_ty) = elem_types.get(&start) else {
            continue;
        };
        if !is_owned_type(start_ty) {
            continue;
        }

        let mut chain = vec![start];
        let mut current = start;

        loop {
            let name = let_binding_name(&block.stmts[current]).expect("simple let");

            // The interior of a chain requires the single-use condition: the
            // current name must be read exactly once in the whole block scope.
            // A name re-bound elsewhere in the block is unsafe to unify, so the
            // binding count must be exactly one (its own definition).
            if count_bindings_in_block(block, name) != 1 {
                break;
            }
            if count_reads_in_block(block, name) != 1 {
                break;
            }

            // The single read must land in the initialiser of a later simple
            // `let` of this block (the handoff to the next chain element).
            let Some(next) = next_let_reading(block, current, name) else {
                break;
            };
            if consumed.contains(&next) {
                break;
            }

            // M-Shadow recovers names "introduced for the same source variable",
            // which the rewrite collapses to one `let mut`.  The recoverable
            // proxy for "same logical variable" is that consecutive elements
            // share one owned type: a value used merely as an argument while a
            // different-typed result is produced (e.g. `flag` feeding a
            // `color_tint(flag, x)` that yields a colour) is *not* a shadowed
            // continuation and must not be unified.
            //
            // The shared *owned* type also discharges `NoEsc(x)`: an owned,
            // non-reference value cannot carry a live borrow of the previous
            // value of `x` past the assignment.
            let (Some(cur_ty), Some(next_ty)) =
                (elem_types.get(&current), elem_types.get(&next))
            else {
                break;
            };
            if !is_owned_type(next_ty) || !types_equal(cur_ty, next_ty) {
                break;
            }

            chain.push(next);
            current = next;
        }

        if chain.len() >= 2 {
            for &idx in &chain {
                consumed.insert(idx);
            }
            chains.push(chain);
        }
    }

    chains
}

/// Find the first simple-`let` statement after `from` whose initialiser reads
/// `name`.  With the single-use condition already checked, this is the handoff
/// target if it exists.
fn next_let_reading(block: &Block, from: usize, name: &str) -> Option<usize> {
    block
        .stmts
        .iter()
        .enumerate()
        .skip(from + 1)
        .find(|(_, stmt)| match stmt {
            Statement::Let(let_stmt) if is_binding_ident(&let_stmt.name) => let_stmt
                .init
                .as_ref()
                .is_some_and(|init| count_reads_in_expr(init, name) >= 1),
            _ => false,
        })
        .map(|(idx, _)| idx)
}

/// Seed a type environment from a function's parameters.
fn function_param_env(function: &FunctionDef) -> TypeEnv {
    function
        .params
        .iter()
        .filter(|param| !param.name.is_empty())
        .map(|param| (param.name.clone(), param.ty.clone()))
        .collect()
}

/// Strip one layer of shared/mutable reference (`&T` → `T`).
fn strip_ref(ty: Type) -> Type {
    match ty {
        Type::Reference(inner, true, _) => *inner,
        other => other,
    }
}

/// A value of this type can be held by a single `let mut` binding and cannot
/// itself carry a borrow of a previous value (no references/slices at the top).
fn is_owned_type(ty: &Type) -> bool {
    !matches!(ty, Type::Reference(_, _, _) | Type::Slice(_))
}

fn binop_returns_bool(op: &str) -> bool {
    matches!(op, "==" | "!=" | "<" | "<=" | ">" | ">=" | "&&" | "||")
}

/// Structural type equality (no inference variables).
fn types_equal(a: &Type, b: &Type) -> bool {
    match (a, b) {
        (Type::Named(x), Type::Named(y)) => x == y,
        (Type::Path(x), Type::Path(y)) => x == y,
        (Type::Generic(xn, xp), Type::Generic(yn, yp)) => {
            xn == yn && xp.len() == yp.len() && xp.iter().zip(yp).all(|(p, q)| types_equal(p, q))
        }
        (Type::Tuple(x), Type::Tuple(y)) => {
            x.len() == y.len() && x.iter().zip(y).all(|(p, q)| types_equal(p, q))
        }
        (Type::Array(x, n), Type::Array(y, m)) => n == m && types_equal(x, y),
        (Type::Slice(x), Type::Slice(y)) => types_equal(x, y),
        (Type::Reference(x, xr, xm), Type::Reference(y, yr, ym)) => {
            xr == yr && xm == ym && types_equal(x, y)
        }
        (Type::Unit, Type::Unit) | (Type::Never, Type::Never) => true,
        _ => false,
    }
}

// ── M-LastUse: backward-liveness clone elimination ───────────────────────────

/// Collect the set of variables that definitely hold *owned* (non-reference)
/// values, so that `v.clone()` can be safely rewritten to a move of `v`.
///
/// We only add a name when its origin is unambiguously owned; anything uncertain
/// (notably match-bound variables, which the borrow pass may have given a `&F`
/// type) is left out, and clones on those receivers are never stripped.
fn compute_owned(function: &FunctionDef) -> HashSet<String> {
    let mut owned = HashSet::new();

    for param in &function.params {
        if !param.name.is_empty() && !is_reference_type(&param.ty) {
            owned.insert(param.name.clone());
        }
    }

    collect_owned_block(&function.body, &mut owned);
    owned
}

fn collect_owned_block(block: &Block, owned: &mut HashSet<String>) {
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if is_binding_ident(&let_stmt.name) {
                    let is_owned = match &let_stmt.ty {
                        Some(ty) => !is_reference_type(ty),
                        None => let_stmt
                            .init
                            .as_ref()
                            .is_some_and(produces_owned_value),
                    };
                    if is_owned {
                        owned.insert(let_stmt.name.clone());
                    }
                }
                if let Some(init) = &let_stmt.init {
                    collect_owned_expr(init, owned);
                }
            }
            Statement::Expr(expr) => collect_owned_expr(expr, owned),
            Statement::Item(item) => {
                if let Item::Function(function) = item.as_ref() {
                    collect_owned_block(&function.body, owned);
                }
            }
            _ => {}
        }
    }
    if let Some(tail) = &block.expr {
        collect_owned_expr(tail, owned);
    }
}

fn collect_owned_expr(expr: &Expr, owned: &mut HashSet<String>) {
    match expr {
        Expr::Block(block) => collect_owned_block(block, owned),
        Expr::Loop(block) | Expr::Unsafe(block) => collect_owned_block(block, owned),
        Expr::If {
            then_branch,
            else_branch,
            ..
        }
        | Expr::IfLet {
            then_branch,
            else_branch,
            ..
        } => {
            collect_owned_block(then_branch, owned);
            if let Some(else_branch) = else_branch {
                collect_owned_block(else_branch, owned);
            }
        }
        Expr::Match { arms, .. } => {
            for arm in arms {
                collect_owned_block(&arm.body, owned);
            }
        }
        Expr::Call(callee, args) => {
            collect_owned_expr(callee, owned);
            args.iter().for_each(|a| collect_owned_expr(a, owned));
        }
        Expr::MethodCall(receiver, _, args) => {
            collect_owned_expr(receiver, owned);
            args.iter().for_each(|a| collect_owned_expr(a, owned));
        }
        Expr::Tuple(items) => items.iter().for_each(|i| collect_owned_expr(i, owned)),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            collect_owned_expr(l, owned);
            collect_owned_expr(r, owned);
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => collect_owned_expr(inner, owned),
        Expr::Closure(_, body, _) => collect_owned_expr(body, owned),
        Expr::Ident(_) | Expr::Path(_, _) | Expr::Literal(_) | Expr::BuilderChain(_) => {}
    }
}

/// Whether evaluating `expr` yields an owned (non-reference) value.  Used only
/// as a conservative heuristic for the `owned` set, so unknown shapes return
/// `false`.
fn produces_owned_value(expr: &Expr) -> bool {
    match expr {
        Expr::MethodCall(_, method, args) if method == "clone" && args.is_empty() => true,
        Expr::Call(_, _) => true,
        Expr::Literal(_) => true,
        Expr::Tuple(_) => true,
        Expr::BinaryOp(_, _, _) => true,
        Expr::Parenthesized(inner) => produces_owned_value(inner),
        Expr::Block(block) => block.expr.as_ref().is_some_and(|tail| produces_owned_value(tail)),
        _ => false,
    }
}

/// Backward-liveness walk of a block: `live` holds the set of variables read in
/// the continuation (everything that executes after this block).  On return,
/// `live` is updated to the variables live on entry to the block.
fn rewrite_lastuse_block(block: &mut Block, live: &mut HashSet<String>, owned: &HashSet<String>) {
    // The tail expression executes last.
    if let Some(tail) = &mut block.expr {
        rewrite_lastuse_expr(tail, live, owned);
    }

    // Statements execute in source order, so liveness flows backward.
    for stmt in block.stmts.iter_mut().rev() {
        match stmt {
            Statement::Let(let_stmt) => {
                // The binding kills the name for everything before it.
                if is_binding_ident(&let_stmt.name) {
                    live.remove(&let_stmt.name);
                }
                if let Some(init) = &mut let_stmt.init {
                    rewrite_lastuse_expr(init, live, owned);
                }
            }
            Statement::Expr(expr) => rewrite_lastuse_expr(expr, live, owned),
            Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {}
        }
    }
}

fn rewrite_lastuse_expr(expr: &mut Expr, live: &mut HashSet<String>, owned: &HashSet<String>) {
    match expr {
        Expr::Ident(name) => {
            live.insert(name.clone());
        }
        Expr::Path(path, PathType::Member) => {
            if let Some(head) = path.first() {
                live.insert(head.clone());
            }
        }
        Expr::Path(_, _) | Expr::Literal(_) => {}

        // M-LastUse: `v.clone()` → `v` when `v` is owned and dead afterwards.
        Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
            if let Expr::Ident(var) = receiver.as_ref() {
                let var = var.clone();
                if owned.contains(&var) && !live.contains(&var) {
                    *expr = Expr::Ident(var.clone());
                }
                // Either way this is a read of `var`.
                live.insert(var);
            } else {
                rewrite_lastuse_expr(receiver, live, owned);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            // Evaluation order is receiver then args, so walk backward.
            for arg in args.iter_mut().rev() {
                rewrite_lastuse_expr(arg, live, owned);
            }
            rewrite_lastuse_expr(receiver, live, owned);
        }
        Expr::Call(callee, args) => {
            for arg in args.iter_mut().rev() {
                rewrite_lastuse_expr(arg, live, owned);
            }
            rewrite_lastuse_expr(callee, live, owned);
        }
        Expr::BinaryOp(left, _, right) => {
            rewrite_lastuse_expr(right, live, owned);
            rewrite_lastuse_expr(left, live, owned);
        }
        Expr::Assign(left, right) => {
            // `x = rhs` overwrites `x`: the old value is dead after this
            // statement, so reads of `x` inside `rhs` are last uses.
            if let Expr::Ident(target) = left.as_ref() {
                live.remove(target);
                rewrite_lastuse_expr(right, live, owned);
            } else {
                rewrite_lastuse_expr(right, live, owned);
                rewrite_lastuse_expr(left, live, owned);
            }
        }
        Expr::Tuple(items) => {
            for item in items.iter_mut().rev() {
                rewrite_lastuse_expr(item, live, owned);
            }
        }
        Expr::Parenthesized(inner) | Expr::UnaryOp(_, inner) => {
            rewrite_lastuse_expr(inner, live, owned)
        }
        Expr::Reference(inner, _, _) => rewrite_lastuse_expr(inner, live, owned),
        Expr::Index(base, index) => {
            rewrite_lastuse_expr(index, live, owned);
            rewrite_lastuse_expr(base, live, owned);
        }
        Expr::Block(block) => rewrite_lastuse_block(block, live, owned),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            let mut then_live = live.clone();
            rewrite_lastuse_block(then_branch, &mut then_live, owned);
            let mut else_live = live.clone();
            if let Some(else_branch) = else_branch {
                rewrite_lastuse_block(else_branch, &mut else_live, owned);
            }
            *live = union(then_live, else_live);
            rewrite_lastuse_expr(condition, live, owned);
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            let mut then_live = live.clone();
            rewrite_lastuse_block(then_branch, &mut then_live, owned);
            let mut else_live = live.clone();
            if let Some(else_branch) = else_branch {
                rewrite_lastuse_block(else_branch, &mut else_live, owned);
            }
            *live = union(then_live, else_live);
            rewrite_lastuse_expr(value, live, owned);
        }
        Expr::Match { expr, arms } => {
            let mut merged = HashSet::new();
            for arm in arms.iter_mut() {
                let mut arm_live = live.clone();
                rewrite_lastuse_block(&mut arm.body, &mut arm_live, owned);
                if let Some(guard) = &mut arm.guard {
                    rewrite_lastuse_expr(guard, &mut arm_live, owned);
                }
                merged.extend(arm_live);
            }
            *live = merged;
            rewrite_lastuse_expr(expr, live, owned);
        }

        // Constructs whose control flow this pass does not model precisely
        // (loops, closures captured by reference, async, builder chains): treat
        // every variable they mention as live and strip nothing inside them.
        Expr::Loop(block) | Expr::Unsafe(block) => collect_live_block(block, live),
        Expr::Await(inner) => collect_live_expr(inner, live),
        Expr::Closure(_, body, _) => collect_live_expr(body, live),
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    collect_live_expr(closure, live);
                }
            }
        }
    }
}

fn union(mut a: HashSet<String>, b: HashSet<String>) -> HashSet<String> {
    a.extend(b);
    a
}

/// Add every variable read anywhere in `expr` to `live` (used for constructs
/// processed conservatively).
fn collect_live_expr(expr: &Expr, live: &mut HashSet<String>) {
    match expr {
        Expr::Ident(name) => {
            live.insert(name.clone());
        }
        Expr::Path(path, PathType::Member) => {
            if let Some(head) = path.first() {
                live.insert(head.clone());
            }
        }
        Expr::Path(_, _) | Expr::Literal(_) => {}
        Expr::Call(callee, args) => {
            collect_live_expr(callee, live);
            args.iter().for_each(|a| collect_live_expr(a, live));
        }
        Expr::MethodCall(receiver, _, args) => {
            collect_live_expr(receiver, live);
            args.iter().for_each(|a| collect_live_expr(a, live));
        }
        Expr::Tuple(items) => items.iter().for_each(|i| collect_live_expr(i, live)),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            collect_live_expr(l, live);
            collect_live_expr(r, live);
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => collect_live_expr(inner, live),
        Expr::Closure(_, body, _) => collect_live_expr(body, live),
        Expr::Block(block) => collect_live_block(block, live),
        Expr::Loop(block) | Expr::Unsafe(block) => collect_live_block(block, live),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            collect_live_expr(condition, live);
            collect_live_block(then_branch, live);
            if let Some(else_branch) = else_branch {
                collect_live_block(else_branch, live);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            collect_live_expr(value, live);
            collect_live_block(then_branch, live);
            if let Some(else_branch) = else_branch {
                collect_live_block(else_branch, live);
            }
        }
        Expr::Match { expr, arms } => {
            collect_live_expr(expr, live);
            for arm in arms {
                if let Some(guard) = &arm.guard {
                    collect_live_expr(guard, live);
                }
                collect_live_block(&arm.body, live);
            }
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    collect_live_expr(closure, live);
                }
            }
        }
    }
}

fn collect_live_block(block: &Block, live: &mut HashSet<String>) {
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &let_stmt.init {
                    collect_live_expr(init, live);
                }
            }
            Statement::Expr(expr) => collect_live_expr(expr, live),
            _ => {}
        }
    }
    if let Some(tail) = &block.expr {
        collect_live_expr(tail, live);
    }
}

// ── Read counting and renaming ───────────────────────────────────────────────

fn count_reads_in_block(block: &Block, name: &str) -> usize {
    let mut count = 0;
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &let_stmt.init {
                    count += count_reads_in_expr(init, name);
                }
            }
            Statement::Expr(expr) => count += count_reads_in_expr(expr, name),
            _ => {}
        }
    }
    if let Some(tail) = &block.expr {
        count += count_reads_in_expr(tail, name);
    }
    count
}

fn count_reads_in_expr(expr: &Expr, name: &str) -> usize {
    match expr {
        Expr::Ident(id) => usize::from(id == name),
        Expr::Path(path, PathType::Member) => usize::from(path.first().is_some_and(|h| h == name)),
        Expr::Path(_, _) | Expr::Literal(_) | Expr::BuilderChain(_) => 0,
        Expr::Call(callee, args) => {
            count_reads_in_expr(callee, name)
                + args.iter().map(|a| count_reads_in_expr(a, name)).sum::<usize>()
        }
        Expr::MethodCall(receiver, _, args) => {
            count_reads_in_expr(receiver, name)
                + args.iter().map(|a| count_reads_in_expr(a, name)).sum::<usize>()
        }
        Expr::Tuple(items) => items.iter().map(|i| count_reads_in_expr(i, name)).sum(),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            count_reads_in_expr(l, name) + count_reads_in_expr(r, name)
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => count_reads_in_expr(inner, name),
        Expr::Closure(_, body, _) => count_reads_in_expr(body, name),
        Expr::Block(block) => count_reads_in_block(block, name),
        Expr::Loop(block) | Expr::Unsafe(block) => count_reads_in_block(block, name),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            count_reads_in_expr(condition, name)
                + count_reads_in_block(then_branch, name)
                + else_branch
                    .as_ref()
                    .map_or(0, |b| count_reads_in_block(b, name))
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            count_reads_in_expr(value, name)
                + count_reads_in_block(then_branch, name)
                + else_branch
                    .as_ref()
                    .map_or(0, |b| count_reads_in_block(b, name))
        }
        Expr::Match { expr, arms } => {
            count_reads_in_expr(expr, name)
                + arms
                    .iter()
                    .map(|arm| {
                        arm.guard.as_ref().map_or(0, |g| count_reads_in_expr(g, name))
                            + count_reads_in_block(&arm.body, name)
                    })
                    .sum::<usize>()
        }
    }
}

/// Count the binding occurrences of `name` within `block` (its own scope).  Used
/// to reject chains whose name is shadowed, since renaming would then be unsafe.
fn count_bindings_in_block(block: &Block, name: &str) -> usize {
    let mut count = 0;
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if is_binding_ident(&let_stmt.name) && let_stmt.name == name {
                    count += 1;
                } else if pattern_binds_name(&let_stmt.name, name) {
                    count += 1;
                }
                if let Some(init) = &let_stmt.init {
                    count += count_bindings_in_expr(init, name);
                }
            }
            Statement::Expr(expr) => count += count_bindings_in_expr(expr, name),
            _ => {}
        }
    }
    if let Some(tail) = &block.expr {
        count += count_bindings_in_expr(tail, name);
    }
    count
}

fn count_bindings_in_expr(expr: &Expr, name: &str) -> usize {
    match expr {
        Expr::Block(block) => count_bindings_in_block(block, name),
        Expr::Loop(block) | Expr::Unsafe(block) => count_bindings_in_block(block, name),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            count_bindings_in_expr(condition, name)
                + count_bindings_in_block(then_branch, name)
                + else_branch
                    .as_ref()
                    .map_or(0, |b| count_bindings_in_block(b, name))
        }
        Expr::IfLet {
            pattern,
            value,
            then_branch,
            else_branch,
        } => {
            usize::from(pattern_binds_name(pattern, name))
                + count_bindings_in_expr(value, name)
                + count_bindings_in_block(then_branch, name)
                + else_branch
                    .as_ref()
                    .map_or(0, |b| count_bindings_in_block(b, name))
        }
        Expr::Match { expr, arms } => {
            count_bindings_in_expr(expr, name)
                + arms
                    .iter()
                    .map(|arm| {
                        usize::from(pattern_binds_name(&arm.pattern, name))
                            + arm.guard.as_ref().map_or(0, |g| count_bindings_in_expr(g, name))
                            + count_bindings_in_block(&arm.body, name)
                    })
                    .sum::<usize>()
        }
        Expr::Closure(params, body, _) => {
            usize::from(params.iter().any(|p| closure_param_name(p) == name))
                + count_bindings_in_expr(body, name)
        }
        Expr::Call(callee, args) => {
            count_bindings_in_expr(callee, name)
                + args.iter().map(|a| count_bindings_in_expr(a, name)).sum::<usize>()
        }
        Expr::MethodCall(receiver, _, args) => {
            count_bindings_in_expr(receiver, name)
                + args.iter().map(|a| count_bindings_in_expr(a, name)).sum::<usize>()
        }
        Expr::Tuple(items) => items.iter().map(|i| count_bindings_in_expr(i, name)).sum(),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            count_bindings_in_expr(l, name) + count_bindings_in_expr(r, name)
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => count_bindings_in_expr(inner, name),
        Expr::Ident(_) | Expr::Path(_, _) | Expr::Literal(_) | Expr::BuilderChain(_) => 0,
    }
}

/// Rename every *read* of a variable named in `map` to its mapped name, leaving
/// binding occurrences (let names, patterns) untouched.
fn rename_reads_block(block: &mut Block, map: &HashMap<String, String>) {
    for stmt in &mut block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    rename_reads_expr(init, map);
                }
            }
            Statement::Expr(expr) => rename_reads_expr(expr, map),
            _ => {}
        }
    }
    if let Some(tail) = &mut block.expr {
        rename_reads_expr(tail, map);
    }
}

fn rename_reads_expr(expr: &mut Expr, map: &HashMap<String, String>) {
    match expr {
        Expr::Ident(name) => {
            if let Some(replacement) = map.get(name) {
                *name = replacement.clone();
            }
        }
        Expr::Path(path, PathType::Member) => {
            if let Some(head) = path.first_mut() {
                if let Some(replacement) = map.get(head) {
                    *head = replacement.clone();
                }
            }
        }
        Expr::Path(_, _) | Expr::Literal(_) | Expr::BuilderChain(_) => {}
        Expr::Call(callee, args) => {
            rename_reads_expr(callee, map);
            args.iter_mut().for_each(|a| rename_reads_expr(a, map));
        }
        Expr::MethodCall(receiver, _, args) => {
            rename_reads_expr(receiver, map);
            args.iter_mut().for_each(|a| rename_reads_expr(a, map));
        }
        Expr::Tuple(items) => items.iter_mut().for_each(|i| rename_reads_expr(i, map)),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            rename_reads_expr(l, map);
            rename_reads_expr(r, map);
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => rename_reads_expr(inner, map),
        Expr::Closure(params, body, _) => {
            // A closure parameter shadows the outer name inside the body.
            let shadowed = params.iter().any(|p| map.contains_key(&closure_param_name(p)));
            if !shadowed {
                rename_reads_expr(body, map);
            }
        }
        Expr::Block(block) => rename_reads_block(block, map),
        Expr::Loop(block) | Expr::Unsafe(block) => rename_reads_block(block, map),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            rename_reads_expr(condition, map);
            rename_reads_block(then_branch, map);
            if let Some(else_branch) = else_branch {
                rename_reads_block(else_branch, map);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            rename_reads_expr(value, map);
            rename_reads_block(then_branch, map);
            if let Some(else_branch) = else_branch {
                rename_reads_block(else_branch, map);
            }
        }
        Expr::Match { expr, arms } => {
            rename_reads_expr(expr, map);
            for arm in arms {
                if let Some(guard) = &mut arm.guard {
                    rename_reads_expr(guard, map);
                }
                rename_reads_block(&mut arm.body, map);
            }
        }
    }
}

// ── Small helpers ─────────────────────────────────────────────────────────────

fn is_simple_let_with_init(stmt: &Statement) -> bool {
    matches!(stmt, Statement::Let(let_stmt)
        if is_binding_ident(&let_stmt.name) && let_stmt.init.is_some())
}

fn let_binding_name(stmt: &Statement) -> Option<&str> {
    match stmt {
        Statement::Let(let_stmt) if is_binding_ident(&let_stmt.name) => Some(&let_stmt.name),
        _ => None,
    }
}

fn is_reference_type(ty: &Type) -> bool {
    matches!(ty, Type::Reference(_, true, _))
}

fn ensure_function_comment(function: &mut FunctionDef, comment: &str) {
    if !function.docs.iter().any(|doc| doc.trim() == comment) {
        function.docs.push(comment.to_string());
    }
}

fn closure_param_name(param: &str) -> String {
    param
        .trim_start_matches("mut ")
        .split(':')
        .next()
        .unwrap_or(param)
        .trim()
        .to_string()
}

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

fn is_reserved_pattern_word(input: &str) -> bool {
    matches!(input, "box" | "false" | "mut" | "ref" | "self" | "true")
}

/// Whether the (string) pattern binds a variable called `name`.
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
