use std::collections::HashSet;

use crate::utils::patterns::{closure_param_name, collect_pattern_bindings, is_binding_ident};
use crate::utils::types::is_reference_type;
use rustlightast::*;

/// Eliminate clones whose owned receiver is dead after the clone.
pub fn optimize_last_use(module: &mut RustModule) {
    optimize_module(module);
}

fn optimize_module(module: &mut RustModule) {
    for item in &mut module.items {
        match item {
            Item::Function(function) => rewrite_last_use_clones_in_function(function),
            Item::Impl(impl_block) => {
                for impl_item in &mut impl_block.items {
                    if let ImplItem::Method(method) = impl_item {
                        rewrite_last_use_clones_in_function(method);
                    }
                }
            }
            Item::Mod(inner) => optimize_module(inner),
            _ => {}
        }
    }
}

/// Apply Last-Use Clone Elimination to `function`.
///
/// Borrow inference also applies this rewrite to an analysis-only clone of the
/// function.  A clone removed there denotes an available ownership move and must
/// not be used as evidence for changing its origin to a shared parameter.  The
/// emitted function is left untouched until the dedicated Last-Use pass runs.
pub(crate) fn rewrite_last_use_clones_in_function(function: &mut FunctionDef) {
    // A scoped backward-liveness pass turns `v.clone()` into
    // `v` when `v` is owned and not read afterwards. Isabelle2Rust treats its
    // generated clone calls as ownership adaptations that preserve the
    // represented Isabelle value, so an available last-use move can replace
    // the clone. The rewrite only changes variables whose old binding is dead.
    // TODO: Replace name-keyed `owned` and `live` sets with resolved lexical
    // binding IDs so shadowed bindings and their ownership modes are distinct.
    let owned = function
        .params
        .iter()
        .filter(|param| !param.name.is_empty() && !is_reference_type(&param.ty))
        .map(|param| param.name.clone())
        .collect();
    let mut live: HashSet<String> = HashSet::new();
    rewrite_lastuse_block(&mut function.body, &mut live, &owned);
}

/// Build an analysis-only Last-Use view of one owned expression.
///
/// B-Match uses this occurrence-local preview to distinguish clones that only
/// adapt an owned pattern binding from clones that must remain materialized.
/// The emitted expression is never passed here.
pub(crate) fn rewrite_last_use_clones_in_owned_expr(expr: &mut Expr, owned: &HashSet<String>) {
    let mut live = HashSet::new();
    rewrite_lastuse_expr(expr, &mut live, owned);
}

// ── Last-Use Clone Elimination ───────────────────────────────────────────────

/// Whether evaluating `expr` yields an owned (non-reference) value.  Used only
/// as a conservative heuristic for the `owned` set, so unknown shapes return
/// `false`.
// TODO: Replace this syntax heuristic with type-environment lookup when the
// pass is extended to reference-returning calls and richer Rust types.
fn produces_owned_value(expr: &Expr, owned: &HashSet<String>) -> bool {
    match expr {
        Expr::Ident(name) => owned.contains(name),
        Expr::MethodCall(_, method, args) if method == "clone" && args.is_empty() => true,
        Expr::Call(_, _) => true,
        Expr::Literal(_) => true,
        Expr::Array(items) | Expr::Tuple(items) => {
            items.iter().all(|item| produces_owned_value(item, owned))
        }
        Expr::BinaryOp(_, _, _) => true,
        Expr::UnaryOp(op, inner) if op == "*" => produces_owned_value(inner, owned),
        Expr::Parenthesized(inner) | Expr::Cast(inner, _) => produces_owned_value(inner, owned),
        Expr::Block(block) => {
            let block_owned = owned_flow_for_block(block, owned)
                .into_iter()
                .last()
                .unwrap_or_else(|| owned.clone());
            block
                .expr
                .as_ref()
                .is_some_and(|tail| produces_owned_value(tail, &block_owned))
        }
        _ => false,
    }
}

fn owned_flow_for_block(block: &Block, inherited: &HashSet<String>) -> Vec<HashSet<String>> {
    let mut current = inherited.clone();
    let mut snapshots = Vec::with_capacity(block.stmts.len() + 1);

    for stmt in &block.stmts {
        snapshots.push(current.clone());
        if let Statement::Let(let_stmt) = stmt {
            let binding_is_owned = match &let_stmt.ty {
                Some(ty) => !is_reference_type(ty),
                None => let_stmt
                    .init
                    .as_ref()
                    .is_some_and(|init| produces_owned_value(init, &current)),
            };
            if binding_is_owned {
                collect_owned_binding_names_from_pattern(&let_stmt.name, &mut current);
            }
        }
    }

    snapshots.push(current);
    snapshots
}

/// Backward-liveness walk of a block: `live` holds the set of variables read in
/// the continuation (everything that executes after this block).  On return,
/// `live` is updated to the variables live on entry to the block.
fn rewrite_lastuse_block(block: &mut Block, live: &mut HashSet<String>, owned: &HashSet<String>) {
    let owned_at = owned_flow_for_block(block, owned);
    // Names already live after the block refer to bindings in the enclosing
    // scope.  A same-named `let` inside this block shadows them only after its
    // initializer has run, so preserve that outer liveness while walking the
    // initializer backward.
    let continuation_live = live.clone();

    // The tail expression executes last.
    if let Some(tail) = &mut block.expr {
        rewrite_lastuse_expr(tail, live, owned_at.last().unwrap_or(owned));
    }

    // Statements execute in source order, so liveness flows backward.
    for (idx, stmt) in block.stmts.iter_mut().enumerate().rev() {
        let stmt_owned = owned_at.get(idx).unwrap_or(owned);
        match stmt {
            Statement::Let(let_stmt) => {
                // The binding kills the name for everything before it.
                remove_pattern_bindings_from_live(&let_stmt.name, live);
                let mut bindings = HashSet::new();
                collect_binding_names_from_pattern(&let_stmt.name, &mut bindings);
                for binding in bindings {
                    if continuation_live.contains(&binding) {
                        live.insert(binding);
                    }
                }
                if let Some(init) = &mut let_stmt.init {
                    rewrite_lastuse_expr(init, live, stmt_owned);
                }
            }
            Statement::Expr(expr) => rewrite_lastuse_expr(expr, live, stmt_owned),
            Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {
            }
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
        // TODO: Track free local reads of opaque macros, or treat such macros
        // as conservative liveness barriers when supporting general Rust.
        Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}

        // `v.clone()` → `v` when `v` is owned and dead afterwards.
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
            // A method receiver may be borrowed for the duration of the call.
            // Keep it, together with explicit borrows in the arguments, live
            // while considering clone-to-move rewrites in sibling arguments.
            collect_live_expr(receiver, live);
            for arg in args.iter() {
                collect_call_borrow_sources(arg, live);
            }
            // Evaluation order is receiver then args, so walk backward.
            for arg in args.iter_mut().rev() {
                rewrite_lastuse_expr(arg, live, owned);
            }
            rewrite_lastuse_expr(receiver, live, owned);
        }
        Expr::Call(callee, args) => {
            // The callee and any argument borrows stay usable until the call
            // completes. In particular, `f(&v, v.clone())` cannot move `v` in
            // the second argument even though that clone is its final read.
            collect_live_expr(callee, live);
            for arg in args.iter() {
                collect_call_borrow_sources(arg, live);
            }
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
                // TODO: Model complex assignees precisely. Rust evaluates the
                // RHS before the assignee, so backward liveness must visit the
                // assignee first and account for the overwritten place.
                rewrite_lastuse_expr(right, live, owned);
                rewrite_lastuse_expr(left, live, owned);
            }
        }
        Expr::Array(items) | Expr::Tuple(items) => {
            for item in items.iter_mut().rev() {
                rewrite_lastuse_expr(item, live, owned);
            }
        }
        Expr::Parenthesized(inner) | Expr::Cast(inner, _) | Expr::UnaryOp(_, inner) => {
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
            pattern,
            value,
            then_branch,
            else_branch,
        } => {
            let mut then_live = live.clone();
            let mut then_owned = owned.clone();
            if produces_owned_value(value, owned) {
                collect_owned_binding_names_from_pattern(pattern, &mut then_owned);
            }
            rewrite_lastuse_block(then_branch, &mut then_live, &then_owned);
            remove_pattern_bindings_from_live(pattern, &mut then_live);

            let mut else_live = live.clone();
            if let Some(else_branch) = else_branch {
                rewrite_lastuse_block(else_branch, &mut else_live, owned);
            }
            *live = union(then_live, else_live);
            rewrite_lastuse_expr(value, live, owned);
        }
        Expr::Match { expr, arms } => {
            let mut merged = HashSet::new();
            let scrutinee_is_owned = produces_owned_value(expr, owned);
            // TODO: Model guard-failure edges to later candidate arms so a
            // guard sees values read by arms that may run when it fails.
            for arm in arms.iter_mut() {
                let mut arm_live = live.clone();
                let mut arm_owned = owned.clone();
                if scrutinee_is_owned {
                    collect_owned_binding_names_from_pattern(&arm.pattern, &mut arm_owned);
                }
                rewrite_lastuse_block(&mut arm.body, &mut arm_live, &arm_owned);
                if let Some(guard) = &mut arm.guard {
                    rewrite_lastuse_expr(guard, &mut arm_live, &arm_owned);
                }
                remove_pattern_bindings_from_live(&arm.pattern, &mut arm_live);
                // Pattern bindings shadow enclosing names only while the arm is
                // evaluated.  If a same-named outer value is live after the
                // match, it must remain live while walking the scrutinee.
                let mut bindings = HashSet::new();
                collect_binding_names_from_pattern(&arm.pattern, &mut bindings);
                for binding in bindings {
                    if live.contains(&binding) {
                        arm_live.insert(binding);
                    }
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
        Expr::Closure(params, body, true) => {
            let closure_owned = params
                .iter()
                .filter(|param| closure_param_is_owned(param))
                .map(|param| closure_param_name(param))
                .collect::<HashSet<_>>();
            let mut closure_live = HashSet::new();
            rewrite_lastuse_expr(body, &mut closure_live, &closure_owned);
            collect_live_closure_body(params, body, live);
        }
        Expr::Closure(params, body, false) => collect_live_closure_body(params, body, live),
        Expr::TypedClosure(params, _, body, true) => {
            let closure_owned = params
                .iter()
                .filter(|param| closure_param_is_owned(param))
                .map(|param| closure_param_name(param))
                .collect();
            let mut closure_live = HashSet::new();
            rewrite_lastuse_expr(body, &mut closure_live, &closure_owned);
            collect_live_closure_body(params, body, live);
        }
        Expr::TypedClosure(params, _, body, false) => collect_live_closure_body(params, body, live),
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    collect_live_expr(closure, live);
                }
            }
        }
    }
}

/// Add variables borrowed by an expression passed as a call argument.
///
/// These borrows may remain live until the surrounding call returns, so a
/// sibling argument must not move their origins. The traversal is conservative
/// for nested expressions: retaining a clone is preferable to emitting a move
/// that overlaps a borrow.
// TODO: Track borrow aliases across statements and propagate liveness from a
// live derived reference back to its origin. This helper currently covers only
// borrows syntactically contained in the surrounding call.
fn collect_call_borrow_sources(expr: &Expr, live: &mut HashSet<String>) {
    match expr {
        Expr::Reference(inner, _, _) => collect_live_expr(inner, live),
        Expr::MethodCall(receiver, method, args) => {
            if method == "as_ref" && args.is_empty() {
                collect_live_expr(receiver, live);
            } else {
                collect_call_borrow_sources(receiver, live);
                for arg in args {
                    collect_call_borrow_sources(arg, live);
                }
            }
        }
        Expr::Call(callee, args) => {
            collect_call_borrow_sources(callee, live);
            for arg in args {
                collect_call_borrow_sources(arg, live);
            }
        }
        Expr::Array(items) | Expr::Tuple(items) => {
            for item in items {
                collect_call_borrow_sources(item, live);
            }
        }
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            collect_call_borrow_sources(left, live);
            collect_call_borrow_sources(right, live);
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Await(inner) => collect_call_borrow_sources(inner, live),
        Expr::Block(block) => {
            collect_call_borrow_sources_block(block, live);
        }
        Expr::Loop(block) | Expr::Unsafe(block) => {
            collect_call_borrow_sources_block(block, live);
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            collect_call_borrow_sources(condition, live);
            collect_call_borrow_sources_block(then_branch, live);
            if let Some(else_branch) = else_branch {
                collect_call_borrow_sources_block(else_branch, live);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            collect_call_borrow_sources(value, live);
            collect_call_borrow_sources_block(then_branch, live);
            if let Some(else_branch) = else_branch {
                collect_call_borrow_sources_block(else_branch, live);
            }
        }
        Expr::Match { expr, arms } => {
            collect_call_borrow_sources(expr, live);
            for arm in arms {
                if let Some(guard) = &arm.guard {
                    collect_call_borrow_sources(guard, live);
                }
                collect_call_borrow_sources_block(&arm.body, live);
            }
        }
        Expr::Closure(_, body, _) | Expr::TypedClosure(_, _, body, _) => {
            collect_call_borrow_sources(body, live)
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    collect_call_borrow_sources(closure, live);
                }
            }
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }
}

fn collect_call_borrow_sources_block(block: &Block, live: &mut HashSet<String>) {
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &let_stmt.init {
                    collect_call_borrow_sources(init, live);
                }
            }
            Statement::Expr(expr) => collect_call_borrow_sources(expr, live),
            Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {
            }
        }
    }
    if let Some(expr) = &block.expr {
        collect_call_borrow_sources(expr, live);
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
        Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
        Expr::Call(callee, args) => {
            collect_live_expr(callee, live);
            args.iter().for_each(|a| collect_live_expr(a, live));
        }
        Expr::MethodCall(receiver, _, args) => {
            collect_live_expr(receiver, live);
            args.iter().for_each(|a| collect_live_expr(a, live));
        }
        Expr::Array(items) | Expr::Tuple(items) => {
            items.iter().for_each(|i| collect_live_expr(i, live))
        }
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            collect_live_expr(l, live);
            collect_live_expr(r, live);
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => collect_live_expr(inner, live),
        Expr::Closure(_, body, _) | Expr::TypedClosure(_, _, body, _) => {
            collect_live_expr(body, live)
        }
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

fn collect_live_closure_body(params: &[ClosureParam], body: &Expr, live: &mut HashSet<String>) {
    let mut body_live = HashSet::new();
    collect_live_expr(body, &mut body_live);
    for param in params {
        body_live.remove(&closure_param_name(param));
    }
    live.extend(body_live);
}

fn closure_param_is_owned(param: &ClosureParam) -> bool {
    let name = closure_param_name(param);
    if !is_binding_ident(&name) {
        return false;
    }

    !matches!(param.ty, Some(Type::Reference(_, true, _)))
}

fn remove_pattern_bindings_from_live(pattern: &str, live: &mut HashSet<String>) {
    let mut bindings = HashSet::new();
    collect_binding_names_from_pattern(pattern, &mut bindings);
    for binding in bindings {
        live.remove(&binding);
    }
}

fn collect_binding_names_from_pattern(pattern: &str, out: &mut HashSet<String>) {
    collect_pattern_bindings(pattern, out, true);
}

fn collect_owned_binding_names_from_pattern(pattern: &str, out: &mut HashSet<String>) {
    collect_pattern_bindings(pattern, out, false);
}

#[cfg(test)]
mod tests {
    use super::*;

    fn named(name: &str) -> Type {
        Type::Named(name.to_string())
    }

    fn ref_to(ty: Type) -> Type {
        Type::Reference(Box::new(ty), true, false)
    }

    fn ident(name: &str) -> Expr {
        Expr::Ident(name.to_string())
    }

    fn clone_call(name: &str) -> Expr {
        Expr::MethodCall(Box::new(ident(name)), "clone".to_string(), vec![])
    }

    fn block_tail(expr: Expr) -> Block {
        Block {
            stmts: vec![],
            expr: Some(Box::new(expr)),
        }
    }

    fn let_stmt(name: &str, init: Expr) -> Statement {
        Statement::Let(LetStmt {
            ifmut: false,
            name: name.to_string(),
            ty: None,
            init: Some(init),
        })
    }

    fn function(param_ty: Type, body: Block) -> FunctionDef {
        FunctionDef {
            name: "get".to_string(),
            params: vec![Param {
                name: "x0".to_string(),
                ty: param_ty,
            }],
            return_type: named("Int"),
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

    fn optimized_function(module: &RustModule) -> &FunctionDef {
        let Item::Function(function) = &module.items[0] else {
            panic!("expected function")
        };
        function
    }

    #[test]
    fn lastuse_removes_clone_from_owned_match_let_binding() {
        let arm_body = Block {
            stmts: vec![let_stmt("x", ident("p0"))],
            expr: Some(Box::new(clone_call("x"))),
        };
        let body = block_tail(Expr::Match {
            expr: Box::new(ident("x0")),
            arms: vec![MatchArm {
                pattern: "Aoption::Somea(p0)".to_string(),
                guard: None,
                body: arm_body,
            }],
        });
        let mut module = module_with(function(named("Aoption"), body));

        optimize_last_use(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Match { arms, .. }) = function.body.expr.as_deref() else {
            panic!("expected match")
        };
        assert_eq!(arms[0].body.stmts.len(), 1);
        assert!(matches!(
            arms[0].body.expr.as_deref(),
            Some(Expr::Ident(name)) if name == "x"
        ));
    }

    #[test]
    fn lastuse_removes_trailing_box_extraction_clone() {
        let arm_body = Block {
            stmts: vec![let_stmt(
                "left",
                Expr::UnaryOp("*".to_string(), Box::new(ident("p0"))),
            )],
            expr: Some(Box::new(clone_call("left"))),
        };
        let body = block_tail(Expr::Match {
            expr: Box::new(ident("x0")),
            arms: vec![MatchArm {
                pattern: "Tree::Node(p0, _, _)".to_string(),
                guard: None,
                body: arm_body,
            }],
        });
        let mut module = module_with(function(named("Tree"), body));

        optimize_last_use(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Match { arms, .. }) = function.body.expr.as_deref() else {
            panic!("expected match")
        };
        assert_eq!(arms[0].body.stmts.len(), 1);
        assert!(matches!(
            arms[0].body.expr.as_deref(),
            Some(Expr::Ident(name)) if name == "left"
        ));
    }

    #[test]
    fn lastuse_removes_clone_after_owned_box_extraction() {
        let arm_body = Block {
            stmts: vec![let_stmt(
                "bop",
                Expr::UnaryOp("*".to_string(), Box::new(ident("p0"))),
            )],
            expr: Some(Box::new(Expr::Call(
                Box::new(ident("mugetb")),
                vec![clone_call("bop")],
            ))),
        };
        let body = block_tail(Expr::Match {
            expr: Box::new(ident("x0")),
            arms: vec![MatchArm {
                pattern: "Aoption::MutualReca(p0)".to_string(),
                guard: None,
                body: arm_body,
            }],
        });
        let mut module = module_with(function(named("Aoption"), body));

        optimize_last_use(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Match { arms, .. }) = function.body.expr.as_deref() else {
            panic!("expected match")
        };
        let Some(Expr::Call(_, args)) = arms[0].body.expr.as_deref() else {
            panic!("expected call")
        };
        assert!(matches!(&args[0], Expr::Ident(name) if name == "bop"));
    }

    #[test]
    fn lastuse_keeps_clone_from_borrowed_match_binding() {
        let arm_body = block_tail(clone_call("p0"));
        let body = block_tail(Expr::Match {
            expr: Box::new(ident("x0")),
            arms: vec![MatchArm {
                pattern: "Aoption::Somea(p0)".to_string(),
                guard: None,
                body: arm_body,
            }],
        });
        let mut module = module_with(function(ref_to(named("Aoption")), body));

        optimize_last_use(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Match { arms, .. }) = function.body.expr.as_deref() else {
            panic!("expected match")
        };
        let Some(tail) = arms[0].body.expr.as_deref() else {
            panic!("expected arm tail")
        };
        assert!(matches!(
            tail,
            Expr::MethodCall(receiver, method, args)
                if matches!(receiver.as_ref(), Expr::Ident(name) if name == "p0")
                    && method == "clone"
                    && args.is_empty()
        ));
    }

    #[test]
    fn lastuse_keeps_clone_from_borrowed_tuple_match_binding() {
        let arm_body = block_tail(clone_call("p0"));
        let body = block_tail(Expr::Match {
            expr: Box::new(Expr::Tuple(vec![ident("x0"), ident("y0")])),
            arms: vec![MatchArm {
                pattern: "(Aoption::Somea(p0), _)".to_string(),
                guard: None,
                body: arm_body,
            }],
        });
        let mut function = function(ref_to(named("Aoption")), body);
        function.params.push(Param {
            name: "y0".to_string(),
            ty: ref_to(named("Aoption")),
        });
        let mut module = module_with(function);

        optimize_last_use(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Match { arms, .. }) = function.body.expr.as_deref() else {
            panic!("expected match")
        };
        let Some(tail) = arms[0].body.expr.as_deref() else {
            panic!("expected arm tail")
        };
        assert!(matches!(
            tail,
            Expr::MethodCall(receiver, method, args)
                if matches!(receiver.as_ref(), Expr::Ident(name) if name == "p0")
                    && method == "clone"
                    && args.is_empty()
        ));
    }

    #[test]
    fn lastuse_keeps_clone_while_shared_borrow_is_live_in_call() {
        let body = block_tail(Expr::Call(
            Box::new(ident("plus_nat")),
            vec![
                Expr::Reference(Box::new(ident("x0")), true, false),
                clone_call("x0"),
            ],
        ));
        let mut module = module_with(function(named("Nat"), body));

        optimize_last_use(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Call(_, args)) = function.body.expr.as_deref() else {
            panic!("expected call")
        };
        assert!(matches!(
            &args[1],
            Expr::MethodCall(receiver, method, method_args)
                if matches!(receiver.as_ref(), Expr::Ident(name) if name == "x0")
                    && method == "clone"
                    && method_args.is_empty()
        ));
    }

    #[test]
    fn lastuse_moves_final_clone_across_owned_call_arguments() {
        let body = block_tail(Expr::Call(
            Box::new(ident("pair")),
            vec![clone_call("x0"), clone_call("x0")],
        ));
        let mut module = module_with(function(named("Nat"), body));

        optimize_last_use(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Call(_, args)) = function.body.expr.as_deref() else {
            panic!("expected call")
        };
        assert!(matches!(&args[1], Expr::Ident(name) if name == "x0"));
        assert!(matches!(&args[0], Expr::MethodCall(_, method, _) if method == "clone"));
    }

    #[test]
    fn lastuse_preserves_outer_value_across_shadowing_block_initializer() {
        let shadowing_block = Expr::Block(Block {
            stmts: vec![let_stmt(
                "(m, x0)",
                Expr::Tuple(vec![
                    Expr::Literal(Literal::Raw("0".to_string())),
                    clone_call("x0"),
                ]),
            )],
            expr: Some(Box::new(ident("m"))),
        });
        let body = block_tail(Expr::Call(
            Box::new(ident("pair")),
            vec![shadowing_block, clone_call("x0")],
        ));
        let mut module = module_with(function(named("Nat"), body));

        optimize_last_use(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Call(_, args)) = function.body.expr.as_deref() else {
            panic!("expected call")
        };
        let Expr::Block(block) = &args[0] else {
            panic!("expected shadowing block")
        };
        let Statement::Let(let_stmt) = &block.stmts[0] else {
            panic!("expected tuple binding")
        };
        let Some(Expr::Tuple(init)) = &let_stmt.init else {
            panic!("expected tuple initializer")
        };
        assert!(matches!(
            &init[1],
            Expr::MethodCall(receiver, method, method_args)
                if matches!(receiver.as_ref(), Expr::Ident(name) if name == "x0")
                    && method == "clone"
                    && method_args.is_empty()
        ));
        assert!(matches!(&args[1], Expr::Ident(name) if name == "x0"));
    }

    #[test]
    fn lastuse_preserves_outer_value_across_shadowing_match_pattern() {
        let shadowing_match = Expr::Match {
            expr: Box::new(Expr::Tuple(vec![
                Expr::Literal(Literal::Raw("0".to_string())),
                clone_call("x0"),
            ])),
            arms: vec![MatchArm {
                pattern: "(m, x0)".to_string(),
                guard: None,
                body: block_tail(ident("m")),
            }],
        };
        let body = block_tail(Expr::Call(
            Box::new(ident("pair")),
            vec![shadowing_match, clone_call("x0")],
        ));
        let mut module = module_with(function(named("Nat"), body));

        optimize_last_use(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Call(_, args)) = function.body.expr.as_deref() else {
            panic!("expected call")
        };
        let Expr::Match { expr, .. } = &args[0] else {
            panic!("expected shadowing match")
        };
        let Expr::Tuple(scrutinee) = expr.as_ref() else {
            panic!("expected tuple scrutinee")
        };
        assert!(matches!(
            &scrutinee[1],
            Expr::MethodCall(receiver, method, method_args)
                if matches!(receiver.as_ref(), Expr::Ident(name) if name == "x0")
                    && method == "clone"
                    && method_args.is_empty()
        ));
        assert!(matches!(&args[1], Expr::Ident(name) if name == "x0"));
    }
}
