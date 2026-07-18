use std::collections::{HashMap, HashSet};

use rustlightast::*;

/// Result of representation-preserving closure cleanup.
#[derive(Debug, Clone, Default)]
pub struct ClosureOptAnalysis {
    /// Number of generated `let x_cap = x;` bindings folded into direct
    /// by-value captures of `x`.
    pub capture_alias_eliminations: usize,
    /// Number of generated forwarding closures replaced by the backend-owned
    /// closure value they merely invoke.
    pub eta_forwarder_eliminations: usize,
}

/// Remove generated capture aliases and redundant forwarding closures.
///
/// M-LastUse may turn a generated capture preparation
/// `let x_cap = x.clone();` into the pure move `let x_cap = x;`.  When that
/// binding is the final statement before a directly returned `Rc::new(move
/// |...| ...)` closure, this pass removes the alias and makes the closure
/// capture `x` directly.  The pass also eta-reduces a directly returned
/// `Rc::new(move |x| (*factory(...))(x))` when `factory` is a backend-owned
/// function whose construction path consists solely of generated capture moves
/// and returning another `Rc::new(move |...| ...)`.  It deliberately does not
/// beta-reduce immediately invoked closures or inline the factory body.
pub fn optimize_closure(module: &mut RustModule) -> ClosureOptAnalysis {
    let mut analysis = ClosureOptAnalysis::default();
    optimize_module(module, &mut analysis);
    analysis
}

fn optimize_module(module: &mut RustModule, analysis: &mut ClosureOptAnalysis) {
    let closure_factories = collect_closure_factories(module);
    for item in &mut module.items {
        optimize_item(item, &closure_factories, analysis);
    }
}

fn optimize_item(
    item: &mut Item,
    closure_factories: &HashMap<String, usize>,
    analysis: &mut ClosureOptAnalysis,
) {
    match item {
        Item::Function(function) => optimize_block(&mut function.body, closure_factories, analysis),
        Item::Impl(impl_block) => {
            for item in &mut impl_block.items {
                match item {
                    ImplItem::Method(method) => {
                        optimize_block(&mut method.body, closure_factories, analysis)
                    }
                    ImplItem::AssocConst(_, _, expr) => {
                        optimize_expr(expr, closure_factories, analysis)
                    }
                    ImplItem::AssocType(_, _) => {}
                }
            }
        }
        Item::Const(const_def) => optimize_expr(&mut const_def.value, closure_factories, analysis),
        Item::LazyStatic(lazy_static) => {
            optimize_block(&mut lazy_static.init, closure_factories, analysis)
        }
        Item::Mod(inner) => optimize_module(inner, analysis),
        _ => {}
    }
}

fn optimize_block(
    block: &mut Block,
    closure_factories: &HashMap<String, usize>,
    analysis: &mut ClosureOptAnalysis,
) {
    // Clean statement initializers first.  Fold this block's capture suffix
    // before visiting the tail so eta-reduction sees the original captured
    // names rather than leaving now-redundant `_cap` moves behind.
    for stmt in &mut block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    optimize_expr(init, closure_factories, analysis);
                }
            }
            Statement::Expr(expr) => optimize_expr(expr, closure_factories, analysis),
            Statement::Item(item) => optimize_item(item, closure_factories, analysis),
            Statement::Continue | Statement::Break | Statement::Comment(_) => {}
        }
    }
    eliminate_capture_alias_suffix(block, analysis);

    if let Some(tail) = &mut block.expr {
        optimize_expr(tail, closure_factories, analysis);
    }

    // Nested rewrites can expose another generated suffix.
    eliminate_capture_alias_suffix(block, analysis);
}

fn optimize_expr(
    expr: &mut Expr,
    closure_factories: &HashMap<String, usize>,
    analysis: &mut ClosureOptAnalysis,
) {
    match expr {
        Expr::Call(callee, args) => {
            optimize_expr(callee, closure_factories, analysis);
            for arg in args {
                optimize_expr(arg, closure_factories, analysis);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            optimize_expr(receiver, closure_factories, analysis);
            for arg in args {
                optimize_expr(arg, closure_factories, analysis);
            }
        }
        Expr::Array(items) | Expr::Tuple(items) => {
            for item in items {
                optimize_expr(item, closure_factories, analysis);
            }
        }
        Expr::Block(block) => optimize_block(block, closure_factories, analysis),
        Expr::Loop(block) | Expr::Unsafe(block) => {
            optimize_block(block, closure_factories, analysis)
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            optimize_expr(condition, closure_factories, analysis);
            optimize_block(then_branch, closure_factories, analysis);
            if let Some(else_branch) = else_branch {
                optimize_block(else_branch, closure_factories, analysis);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            optimize_expr(value, closure_factories, analysis);
            optimize_block(then_branch, closure_factories, analysis);
            if let Some(else_branch) = else_branch {
                optimize_block(else_branch, closure_factories, analysis);
            }
        }
        Expr::Match { expr, arms } => {
            optimize_expr(expr, closure_factories, analysis);
            for arm in arms {
                if let Some(guard) = &mut arm.guard {
                    optimize_expr(guard, closure_factories, analysis);
                }
                optimize_block(&mut arm.body, closure_factories, analysis);
            }
        }
        Expr::Reference(inner, _, _)
        | Expr::UnaryOp(_, inner)
        | Expr::Await(inner)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Closure(_, inner, _)
        | Expr::TypedClosure(_, _, inner, _) => optimize_expr(inner, closure_factories, analysis),
        Expr::Index(base, index) | Expr::Assign(base, index) => {
            optimize_expr(base, closure_factories, analysis);
            optimize_expr(index, closure_factories, analysis);
        }
        Expr::BinaryOp(left, _, right) => {
            optimize_expr(left, closure_factories, analysis);
            optimize_expr(right, closure_factories, analysis);
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    optimize_expr(closure, closure_factories, analysis);
                }
            }
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }

    if eta_reduce_forwarder(expr, closure_factories) {
        analysis.eta_forwarder_eliminations += 1;
    }
}

/// Record local functions whose call performs no eager work other than moving
/// generated `_cap` aliases and returning a move `Rc` closure.  Calls to such
/// functions may be evaluated once when an administrative forwarding closure
/// is built.
fn collect_closure_factories(module: &RustModule) -> HashMap<String, usize> {
    module
        .items
        .iter()
        .filter_map(|item| {
            let Item::Function(function) = item else {
                return None;
            };
            if function
                .body
                .stmts
                .iter()
                .any(|stmt| capture_alias_move(stmt).is_none())
            {
                return None;
            }
            let tail = function.body.expr.as_deref()?;
            let (params, _) = direct_move_rc_closure(tail)?;
            Some((function.name.clone(), params.len()))
        })
        .collect()
}

/// Eta-reduce a backend-generated forwarding closure without opening the
/// closure factory or substituting into its body:
///
/// ```text
/// Rc::new(move |x| (*factory(captures))(x))
///     ==> factory(captures)
/// ```
///
/// Empty blocks, parentheses, and casts around the outer closure are retained.
fn eta_reduce_forwarder(expr: &mut Expr, closure_factories: &HashMap<String, usize>) -> bool {
    match expr {
        Expr::Parenthesized(inner) | Expr::Cast(inner, _) => {
            eta_reduce_forwarder(inner, closure_factories)
        }
        Expr::Block(block) if block.stmts.is_empty() => block
            .expr
            .as_deref_mut()
            .is_some_and(|tail| eta_reduce_forwarder(tail, closure_factories)),
        Expr::Call(callee, outer_args) if is_rc_new(callee) && outer_args.len() == 1 => {
            let Some((params, body)) = move_closure(&outer_args[0]) else {
                return false;
            };
            let Some((forwarded, forwarded_args)) = forwarded_call(body) else {
                return false;
            };
            let Some(factory) = closure_factory_call(forwarded) else {
                return false;
            };
            if closure_factories.get(factory) != Some(&params.len())
                || params.len() != forwarded_args.len()
                || !forwards_params_unchanged(params, forwarded_args)
                || params
                    .iter()
                    .any(|param| count_reads_in_expr(forwarded, &closure_param_name(param)) != 0)
            {
                return false;
            }
            *expr = forwarded.clone();
            true
        }
        _ => false,
    }
}

fn move_closure(expr: &Expr) -> Option<(&[ClosureParam], &Expr)> {
    match strip_parens(expr) {
        Expr::Closure(params, body, true) | Expr::TypedClosure(params, _, body, true) => {
            Some((params, body))
        }
        _ => None,
    }
}

fn forwarded_call(expr: &Expr) -> Option<(&Expr, &[Expr])> {
    let Expr::Call(callee, args) = strip_empty_blocks_and_parens(expr) else {
        return None;
    };
    let Expr::UnaryOp(op, forwarded) = strip_parens(callee) else {
        return None;
    };
    (op == "*").then_some((strip_parens(forwarded), args))
}

fn closure_factory_call(expr: &Expr) -> Option<&str> {
    let Expr::Call(callee, _) = strip_parens(expr) else {
        return None;
    };
    let Expr::Ident(name) = strip_parens(callee) else {
        return None;
    };
    Some(name)
}

fn forwards_params_unchanged(params: &[ClosureParam], args: &[Expr]) -> bool {
    let mut names = HashSet::new();
    params.iter().zip(args).all(|(param, arg)| {
        let name = closure_param_name(param);
        is_binding_ident(&name)
            && names.insert(name.clone())
            && matches!(strip_parens(arg), Expr::Ident(arg_name) if arg_name == &name)
    })
}

fn strip_empty_blocks_and_parens(expr: &Expr) -> &Expr {
    match expr {
        Expr::Parenthesized(inner) => strip_empty_blocks_and_parens(inner),
        Expr::Block(block) if block.stmts.is_empty() => block
            .expr
            .as_deref()
            .map(strip_empty_blocks_and_parens)
            .unwrap_or(expr),
        _ => expr,
    }
}

#[derive(Debug)]
struct CaptureAlias {
    alias: String,
    original: String,
}

/// Fold a contiguous suffix of generated capture moves:
///
/// ```text
/// let x_cap = x;
/// let y_cap = y;
/// Rc::new(move |...| body(x_cap, y_cap))
/// ```
///
/// The suffix restriction keeps the ownership handoff adjacent to closure
/// creation.  Requiring `_cap` names and a direct `Rc::new(move ...)` tail
/// limits the rewrite to the shape emitted by the Isabelle2Rust backend.
fn eliminate_capture_alias_suffix(block: &mut Block, analysis: &mut ClosureOptAnalysis) {
    let Some(tail) = block.expr.as_deref() else {
        return;
    };
    let Some((params, body)) = direct_move_rc_closure(tail) else {
        return;
    };

    let mut start = block.stmts.len();
    let mut aliases = Vec::new();
    for stmt in block.stmts.iter().rev() {
        let Some(alias) = capture_alias_move(stmt) else {
            break;
        };
        start -= 1;
        aliases.push(alias);
    }
    aliases.reverse();
    if aliases.is_empty() {
        return;
    }

    let alias_names = aliases
        .iter()
        .map(|alias| alias.alias.as_str())
        .collect::<HashSet<_>>();
    let original_names = aliases
        .iter()
        .map(|alias| alias.original.as_str())
        .collect::<HashSet<_>>();

    // Reject chains such as `let y_cap = x_cap;`: the cleanup is only for
    // independent moves from the original outer bindings.
    if alias_names.len() != aliases.len()
        || original_names.len() != aliases.len()
        || alias_names.iter().any(|name| original_names.contains(name))
    {
        return;
    }

    let param_names = params
        .iter()
        .map(|param| closure_param_name(param))
        .collect::<HashSet<_>>();

    for alias in &aliases {
        // Renaming `x_cap` to a closure parameter or to a name rebound inside
        // the body would capture the rewritten reads, so keep the alias.
        if param_names.contains(&alias.alias)
            || param_names.contains(&alias.original)
            || binds_name_in_expr(body, &alias.original)
            || count_reads_in_expr(body, &alias.alias) == 0
            || count_reads_in_expr(body, &alias.original) != 0
        {
            return;
        }
    }

    let substitutions = aliases
        .iter()
        .map(|alias| (alias.alias.clone(), Expr::Ident(alias.original.clone())))
        .collect::<HashMap<_, _>>();
    let rewritten_body = subst_idents_in_expr(body, &substitutions);

    let Some((_, body)) = direct_move_rc_closure_mut(
        block
            .expr
            .as_deref_mut()
            .expect("tail expression checked above"),
    ) else {
        return;
    };
    *body = rewritten_body;
    block.stmts.truncate(start);
    analysis.capture_alias_eliminations += aliases.len();
}

fn capture_alias_move(stmt: &Statement) -> Option<CaptureAlias> {
    let Statement::Let(let_stmt) = stmt else {
        return None;
    };
    if let_stmt.ifmut || let_stmt.ty.is_some() || !is_binding_ident(&let_stmt.name) {
        return None;
    }
    if !let_stmt.name.ends_with("_cap") {
        return None;
    }

    let Expr::Ident(original) = let_stmt.init.as_ref().map(strip_parens)? else {
        return None;
    };
    if !is_binding_ident(original) || original == &let_stmt.name {
        return None;
    }

    Some(CaptureAlias {
        alias: let_stmt.name.clone(),
        original: original.clone(),
    })
}

fn direct_move_rc_closure(expr: &Expr) -> Option<(&[ClosureParam], &Expr)> {
    let Expr::Call(callee, args) = strip_capture_wrappers(expr) else {
        return None;
    };
    if !is_rc_new(callee) || args.len() != 1 {
        return None;
    }
    match strip_parens(&args[0]) {
        Expr::Closure(params, body, true) | Expr::TypedClosure(params, _, body, true) => {
            Some((params.as_slice(), body.as_ref()))
        }
        _ => None,
    }
}

fn direct_move_rc_closure_mut(expr: &mut Expr) -> Option<(&[ClosureParam], &mut Expr)> {
    let expr = strip_capture_wrappers_mut(expr);
    let Expr::Call(callee, args) = expr else {
        return None;
    };
    if !is_rc_new(callee) || args.len() != 1 {
        return None;
    }
    match strip_parens_mut(&mut args[0]) {
        Expr::Closure(params, body, true) | Expr::TypedClosure(params, _, body, true) => {
            Some((params.as_slice(), body.as_mut()))
        }
        _ => None,
    }
}

fn is_rc_new(expr: &Expr) -> bool {
    matches!(strip_parens(expr), Expr::Path(path, PathType::Namespace) if path.as_slice() == ["Rc", "new"])
}

fn strip_capture_wrappers(expr: &Expr) -> &Expr {
    match expr {
        Expr::Parenthesized(inner) | Expr::Cast(inner, _) => strip_capture_wrappers(inner),
        other => other,
    }
}

fn strip_capture_wrappers_mut(expr: &mut Expr) -> &mut Expr {
    match expr {
        Expr::Parenthesized(inner) | Expr::Cast(inner, _) => strip_capture_wrappers_mut(inner),
        other => other,
    }
}

fn strip_parens(expr: &Expr) -> &Expr {
    match expr {
        Expr::Parenthesized(inner) => strip_parens(inner),
        other => other,
    }
}

fn strip_parens_mut(expr: &mut Expr) -> &mut Expr {
    match expr {
        Expr::Parenthesized(inner) => strip_parens_mut(inner),
        other => other,
    }
}

fn subst_idents_in_expr(expr: &Expr, subst: &HashMap<String, Expr>) -> Expr {
    match expr {
        Expr::Ident(name) => subst.get(name).cloned().unwrap_or_else(|| expr.clone()),
        Expr::Path(path, PathType::Member) if path.len() == 1 => {
            subst.get(&path[0]).cloned().unwrap_or_else(|| expr.clone())
        }
        Expr::MethodCall(receiver, method, args) => Expr::MethodCall(
            Box::new(subst_idents_in_expr(receiver, subst)),
            method.clone(),
            args.iter()
                .map(|arg| subst_idents_in_expr(arg, subst))
                .collect(),
        ),
        Expr::Call(callee, args) => Expr::Call(
            Box::new(subst_idents_in_expr(callee, subst)),
            args.iter()
                .map(|arg| subst_idents_in_expr(arg, subst))
                .collect(),
        ),
        Expr::Block(block) => Expr::Block(subst_idents_in_block(block, subst)),
        Expr::Array(items) => Expr::Array(
            items
                .iter()
                .map(|item| subst_idents_in_expr(item, subst))
                .collect(),
        ),
        Expr::Tuple(items) => Expr::Tuple(
            items
                .iter()
                .map(|item| subst_idents_in_expr(item, subst))
                .collect(),
        ),
        Expr::BinaryOp(left, op, right) => Expr::BinaryOp(
            Box::new(subst_idents_in_expr(left, subst)),
            op.clone(),
            Box::new(subst_idents_in_expr(right, subst)),
        ),
        Expr::UnaryOp(op, inner) => {
            Expr::UnaryOp(op.clone(), Box::new(subst_idents_in_expr(inner, subst)))
        }
        Expr::Reference(inner, is_ref, mutable) => Expr::Reference(
            Box::new(subst_idents_in_expr(inner, subst)),
            *is_ref,
            *mutable,
        ),
        Expr::Index(base, index) => Expr::Index(
            Box::new(subst_idents_in_expr(base, subst)),
            Box::new(subst_idents_in_expr(index, subst)),
        ),
        Expr::Assign(left, right) => Expr::Assign(
            Box::new(subst_idents_in_expr(left, subst)),
            Box::new(subst_idents_in_expr(right, subst)),
        ),
        Expr::Parenthesized(inner) => {
            Expr::Parenthesized(Box::new(subst_idents_in_expr(inner, subst)))
        }
        Expr::Cast(inner, ty) => {
            Expr::Cast(Box::new(subst_idents_in_expr(inner, subst)), ty.clone())
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => Expr::If {
            condition: Box::new(subst_idents_in_expr(condition, subst)),
            then_branch: subst_idents_in_block(then_branch, subst),
            else_branch: else_branch
                .as_ref()
                .map(|branch| subst_idents_in_block(branch, subst)),
        },
        Expr::IfLet {
            pattern,
            value,
            then_branch,
            else_branch,
        } => Expr::IfLet {
            pattern: pattern.clone(),
            value: Box::new(subst_idents_in_expr(value, subst)),
            then_branch: subst_idents_in_block(
                then_branch,
                &subst_without_pattern_bindings(subst, pattern),
            ),
            else_branch: else_branch
                .as_ref()
                .map(|branch| subst_idents_in_block(branch, subst)),
        },
        Expr::Match { expr, arms } => Expr::Match {
            expr: Box::new(subst_idents_in_expr(expr, subst)),
            arms: arms
                .iter()
                .map(|arm| MatchArm {
                    pattern: arm.pattern.clone(),
                    guard: arm.guard.as_ref().map(|guard| {
                        subst_idents_in_expr(
                            guard,
                            &subst_without_pattern_bindings(subst, &arm.pattern),
                        )
                    }),
                    body: subst_idents_in_block(
                        &arm.body,
                        &subst_without_pattern_bindings(subst, &arm.pattern),
                    ),
                })
                .collect(),
        },
        Expr::Closure(params, body, is_move) => {
            let mut inner_subst = subst.clone();
            for param in params {
                inner_subst.remove(&closure_param_name(param));
            }
            Expr::Closure(
                params.clone(),
                Box::new(subst_idents_in_expr(body, &inner_subst)),
                *is_move,
            )
        }
        Expr::TypedClosure(params, return_type, body, is_move) => {
            let mut inner_subst = subst.clone();
            for param in params {
                inner_subst.remove(&closure_param_name(param));
            }
            Expr::TypedClosure(
                params.clone(),
                return_type.clone(),
                Box::new(subst_idents_in_expr(body, &inner_subst)),
                *is_move,
            )
        }
        Expr::Loop(block) => Expr::Loop(Box::new(subst_idents_in_block(block, subst))),
        Expr::Unsafe(block) => Expr::Unsafe(Box::new(subst_idents_in_block(block, subst))),
        Expr::Await(inner) => Expr::Await(Box::new(subst_idents_in_expr(inner, subst))),
        Expr::BuilderChain(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {
            expr.clone()
        }
    }
}

fn subst_idents_in_block(block: &Block, subst: &HashMap<String, Expr>) -> Block {
    let mut inner = subst.clone();
    let mut stmts = Vec::with_capacity(block.stmts.len());

    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                let init = let_stmt
                    .init
                    .as_ref()
                    .map(|init| subst_idents_in_expr(init, &inner));
                remove_pattern_bindings(&let_stmt.name, &mut inner);
                stmts.push(Statement::Let(LetStmt {
                    ifmut: let_stmt.ifmut,
                    name: let_stmt.name.clone(),
                    ty: let_stmt.ty.clone(),
                    init,
                }));
            }
            Statement::Expr(expr) => {
                stmts.push(Statement::Expr(subst_idents_in_expr(expr, &inner)))
            }
            other => stmts.push(other.clone()),
        }
    }

    Block {
        stmts,
        expr: block
            .expr
            .as_ref()
            .map(|expr| Box::new(subst_idents_in_expr(expr, &inner))),
    }
}

fn count_reads_in_expr(expr: &Expr, name: &str) -> usize {
    match expr {
        Expr::Ident(id) => usize::from(id == name),
        Expr::Path(path, PathType::Member) => {
            usize::from(path.first().is_some_and(|id| id == name))
        }
        Expr::MethodCall(receiver, _, args) => {
            count_reads_in_expr(receiver, name)
                + args
                    .iter()
                    .map(|arg| count_reads_in_expr(arg, name))
                    .sum::<usize>()
        }
        Expr::Call(callee, args) => {
            count_reads_in_expr(callee, name)
                + args
                    .iter()
                    .map(|arg| count_reads_in_expr(arg, name))
                    .sum::<usize>()
        }
        Expr::Block(block) => count_reads_in_block(block, name),
        Expr::Array(items) | Expr::Tuple(items) => items
            .iter()
            .map(|item| count_reads_in_expr(item, name))
            .sum(),
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            count_reads_in_expr(left, name) + count_reads_in_expr(right, name)
        }
        Expr::UnaryOp(_, inner)
        | Expr::Reference(inner, _, _)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Await(inner) => count_reads_in_expr(inner, name),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            count_reads_in_expr(condition, name)
                + count_reads_in_block(then_branch, name)
                + else_branch
                    .as_ref()
                    .map_or(0, |branch| count_reads_in_block(branch, name))
        }
        Expr::IfLet {
            pattern,
            value,
            then_branch,
            else_branch,
        } => {
            count_reads_in_expr(value, name)
                + if pattern_binds_name(pattern, name) {
                    0
                } else {
                    count_reads_in_block(then_branch, name)
                }
                + else_branch
                    .as_ref()
                    .map_or(0, |branch| count_reads_in_block(branch, name))
        }
        Expr::Match { expr, arms } => {
            count_reads_in_expr(expr, name)
                + arms
                    .iter()
                    .map(|arm| {
                        if pattern_binds_name(&arm.pattern, name) {
                            0
                        } else {
                            arm.guard
                                .as_ref()
                                .map_or(0, |guard| count_reads_in_expr(guard, name))
                                + count_reads_in_block(&arm.body, name)
                        }
                    })
                    .sum::<usize>()
        }
        Expr::Closure(params, body, _) | Expr::TypedClosure(params, _, body, _) => {
            if params.iter().any(|param| closure_param_name(param) == name) {
                0
            } else {
                count_reads_in_expr(body, name)
            }
        }
        Expr::Loop(block) | Expr::Unsafe(block) => count_reads_in_block(block, name),
        Expr::BuilderChain(methods) => methods
            .iter()
            .map(|method| match method {
                BuilderMethod::Spawn { closure, .. } => count_reads_in_expr(closure, name),
                BuilderMethod::Named(_) => 0,
            })
            .sum(),
        Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => 0,
    }
}

fn count_reads_in_block(block: &Block, name: &str) -> usize {
    let mut count = 0;
    let mut shadowed = false;
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &let_stmt.init {
                    count += count_reads_in_expr(init, name);
                }
                if pattern_binds_name(&let_stmt.name, name) {
                    shadowed = true;
                    break;
                }
            }
            Statement::Expr(expr) => count += count_reads_in_expr(expr, name),
            Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {
            }
        }
    }
    if !shadowed {
        if let Some(expr) = &block.expr {
            count += count_reads_in_expr(expr, name);
        }
    }
    count
}

fn binds_name_in_expr(expr: &Expr, name: &str) -> bool {
    match expr {
        Expr::Closure(params, body, _) | Expr::TypedClosure(params, _, body, _) => {
            params.iter().any(|param| closure_param_name(param) == name)
                || binds_name_in_expr(body, name)
        }
        Expr::Block(block) => binds_name_in_block(block, name),
        Expr::Loop(block) | Expr::Unsafe(block) => binds_name_in_block(block, name),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            binds_name_in_expr(condition, name)
                || binds_name_in_block(then_branch, name)
                || else_branch
                    .as_ref()
                    .is_some_and(|branch| binds_name_in_block(branch, name))
        }
        Expr::IfLet {
            pattern,
            value,
            then_branch,
            else_branch,
        } => {
            pattern_binds_name(pattern, name)
                || binds_name_in_expr(value, name)
                || binds_name_in_block(then_branch, name)
                || else_branch
                    .as_ref()
                    .is_some_and(|branch| binds_name_in_block(branch, name))
        }
        Expr::Match { expr, arms } => {
            binds_name_in_expr(expr, name)
                || arms.iter().any(|arm| {
                    pattern_binds_name(&arm.pattern, name)
                        || arm
                            .guard
                            .as_ref()
                            .is_some_and(|guard| binds_name_in_expr(guard, name))
                        || binds_name_in_block(&arm.body, name)
                })
        }
        Expr::Call(callee, args) => {
            binds_name_in_expr(callee, name) || args.iter().any(|arg| binds_name_in_expr(arg, name))
        }
        Expr::MethodCall(receiver, _, args) => {
            binds_name_in_expr(receiver, name)
                || args.iter().any(|arg| binds_name_in_expr(arg, name))
        }
        Expr::Array(items) | Expr::Tuple(items) => {
            items.iter().any(|item| binds_name_in_expr(item, name))
        }
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            binds_name_in_expr(left, name) || binds_name_in_expr(right, name)
        }
        Expr::UnaryOp(_, inner)
        | Expr::Reference(inner, _, _)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Await(inner) => binds_name_in_expr(inner, name),
        Expr::BuilderChain(methods) => methods.iter().any(|method| match method {
            BuilderMethod::Spawn { closure, .. } => binds_name_in_expr(closure, name),
            BuilderMethod::Named(_) => false,
        }),
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => false,
    }
}

fn binds_name_in_block(block: &Block, name: &str) -> bool {
    block.stmts.iter().any(|stmt| match stmt {
        Statement::Let(let_stmt) => {
            pattern_binds_name(&let_stmt.name, name)
                || let_stmt
                    .init
                    .as_ref()
                    .is_some_and(|init| binds_name_in_expr(init, name))
        }
        Statement::Expr(expr) => binds_name_in_expr(expr, name),
        Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {
            false
        }
    }) || block
        .expr
        .as_ref()
        .is_some_and(|expr| binds_name_in_expr(expr, name))
}

fn closure_param_name(param: &ClosureParam) -> String {
    param.pattern.trim_start_matches("mut ").trim().to_string()
}

fn is_binding_ident(input: &str) -> bool {
    let mut chars = input.chars();
    let Some(first) = chars.next() else {
        return false;
    };
    (first == '_' || first.is_ascii_alphabetic())
        && input != "_"
        && !matches!(input, "box" | "false" | "mut" | "ref" | "self" | "true")
        && chars.all(|ch| ch == '_' || ch.is_ascii_alphanumeric())
}

fn subst_without_pattern_bindings(
    subst: &HashMap<String, Expr>,
    pattern: &str,
) -> HashMap<String, Expr> {
    let mut inner = subst.clone();
    remove_pattern_bindings(pattern, &mut inner);
    inner
}

fn remove_pattern_bindings(pattern: &str, subst: &mut HashMap<String, Expr>) {
    let names = subst.keys().cloned().collect::<Vec<_>>();
    for name in names {
        if pattern_binds_name(pattern, &name) {
            subst.remove(&name);
        }
    }
}

fn pattern_binds_name(pattern: &str, name: &str) -> bool {
    pattern_binding_tokens(pattern).any(|token| token == name)
}

fn pattern_binding_tokens(pattern: &str) -> impl Iterator<Item = &str> {
    pattern
        .split(|ch: char| !(ch == '_' || ch.is_ascii_alphanumeric()))
        .filter(|token| {
            is_binding_ident(token)
                && !token
                    .chars()
                    .next()
                    .is_some_and(|ch| ch.is_ascii_uppercase())
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::{optimize_mut, parse_rust_source};

    fn optimize_and_print(source: &str) -> (ClosureOptAnalysis, String) {
        let mut module = parse_rust_source(source, "Test").expect("parse source");
        let analysis = optimize_closure(&mut module);
        let mut generator = RustCodeGenerator::new();
        (analysis, generator.generate_module_code(&module))
    }

    fn optimize_stage2_and_print(source: &str) -> (ClosureOptAnalysis, String) {
        let mut module = parse_rust_source(source, "Test").expect("parse source");
        optimize_mut(&mut module);
        let analysis = optimize_closure(&mut module);
        let mut generator = RustCodeGenerator::new();
        (analysis, generator.generate_module_code(&module))
    }

    #[test]
    fn keeps_immediately_invoked_rc_closure() {
        let source = r#"
use std::rc::Rc;

pub fn id_abs<A>(x: A) -> A
where
    A: Clone + 'static,
{
    (*Rc::new(move |xa: A| {
        xa.clone()
    }))(x.clone())
}
"#;

        let (analysis, printed) = optimize_stage2_and_print(source);
        assert_eq!(analysis.capture_alias_eliminations, 0);
        assert!(printed.contains("Rc::new"));
        assert!(printed.contains("move |xa: A|"));
        assert!(printed.contains("}))(x)"));
    }

    #[test]
    fn eliminates_last_use_capture_alias_without_erasing_closure() {
        let source = r#"
use std::rc::Rc;

pub fn make_adder(n: Int) -> Rc<dyn Fn(Int) -> Int> {
    let n_cap = n.clone();
    Rc::new(move |x: Int| {
        plus_int(x.clone(), n_cap.clone())
    })
}
"#;

        let (analysis, printed) = optimize_stage2_and_print(source);
        assert_eq!(analysis.capture_alias_eliminations, 1);
        assert!(!printed.contains("let n_cap"));
        assert!(!printed.contains("n_cap.clone()"));
        assert!(printed.contains("plus_int(x, n.clone())"));
        assert!(printed.contains("Rc::new"));
    }

    #[test]
    fn keeps_cloned_capture_when_original_is_used_later() {
        let source = r#"
use std::rc::Rc;

pub fn make_pair(n: Int) -> (Rc<dyn Fn(Int) -> Int>, Int) {
    let n_cap = n.clone();
    let f = Rc::new(move |x: Int| {
        plus_int(x.clone(), n_cap.clone())
    }) as Rc<dyn Fn(Int) -> Int>;
    (f, n)
}
"#;

        let (analysis, printed) = optimize_stage2_and_print(source);
        assert_eq!(analysis.capture_alias_eliminations, 0);
        assert!(printed.contains("let n_cap = n.clone()"));
        assert!(printed.contains("n_cap.clone()"));
    }

    #[test]
    fn keeps_alias_when_original_name_is_a_closure_parameter() {
        let source = r#"
use std::rc::Rc;

pub fn make_shadow(n: Int) -> Rc<dyn Fn(Int) -> Int> {
    let n_cap = n;
    Rc::new(move |n: Int| {
        plus_int(n, n_cap.clone())
    })
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.capture_alias_eliminations, 0);
        assert!(printed.contains("let n_cap = n"));
        assert!(printed.contains("n_cap.clone()"));
    }

    #[test]
    fn keeps_unused_outer_alias_when_body_shadows_alias_name() {
        let source = r#"
use std::rc::Rc;

pub fn make_shadow(n: Int) -> Rc<dyn Fn(Int) -> Int> {
    let n_cap = n;
    Rc::new(move |x: Int| {
        let n_cap = x;
        n_cap
    })
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.capture_alias_eliminations, 0);
        assert!(printed.contains("let n_cap = n"));
    }

    #[test]
    fn eliminates_multiple_capture_aliases() {
        let source = r#"
use std::rc::Rc;

pub fn make_pair_adder(x: Int, y: Int) -> Rc<dyn Fn(Int) -> Int> {
    let x_cap = x;
    let y_cap = y;
    Rc::new(move |z: Int| {
        plus_int(z, plus_int(x_cap.clone(), y_cap.clone()))
    })
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.capture_alias_eliminations, 2);
        assert!(!printed.contains("let x_cap"));
        assert!(!printed.contains("let y_cap"));
        assert!(printed.contains("plus_int(x.clone(), y.clone())"));
        assert!(printed.contains("Rc::new"));
    }

    #[test]
    fn eta_reduces_forwarder_to_backend_closure_factory() {
        let source = r#"
use std::rc::Rc;

type RegisterFile = Rc<dyn Fn(u8) -> u64>;

pub fn fun_upd(f: RegisterFile, key: u8, value: u64) -> RegisterFile {
    let f_cap = f;
    let key_cap = key;
    let value_cap = value;
    Rc::new(move |x: u8| {
        if x == key_cap { value_cap } else { (*f_cap)(x) }
    })
}

pub fn update(key: u8, value: u64, rs: RegisterFile) -> RegisterFile {
    (({
        Rc::new(move |x: u8| -> u64 {
            (*fun_upd(rs.clone(), key, value))(x)
        })
    }) as RegisterFile)
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.eta_forwarder_eliminations, 1);
        assert!(printed.contains("fun_upd(rs.clone(), key, value)"));
        assert_eq!(printed.matches("Rc::new(move |x: u8|").count(), 1);
    }

    #[test]
    fn keeps_forwarder_to_unknown_factory() {
        let source = r#"
use std::rc::Rc;

type RegisterFile = Rc<dyn Fn(u8) -> u64>;

pub fn update(key: u8, value: u64, rs: RegisterFile) -> RegisterFile {
    Rc::new(move |x: u8| {
        (*external_update(rs.clone(), key, value))(x)
    })
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.eta_forwarder_eliminations, 0);
        assert!(printed.contains("Rc::new(move |x: u8|"));
        assert!(printed.contains("(*external_update(rs.clone(), key, value))(x)"));
    }

    #[test]
    fn keeps_forwarder_that_transforms_its_argument() {
        let source = r#"
use std::rc::Rc;

type RegisterFile = Rc<dyn Fn(u8) -> u64>;

pub fn fun_upd(f: RegisterFile, key: u8, value: u64) -> RegisterFile {
    Rc::new(move |x: u8| {
        if x == key { value } else { (*f)(x) }
    })
}

pub fn update(key: u8, value: u64, rs: RegisterFile) -> RegisterFile {
    Rc::new(move |x: u8| {
        (*fun_upd(rs.clone(), key, value))(x + 1)
    })
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.eta_forwarder_eliminations, 0);
        assert!(printed.contains("Rc::new(move |x: u8|"));
        assert!(printed.contains(")(x + 1)"));
    }

    #[test]
    fn keeps_factory_with_eager_construction_statements() {
        let source = r#"
use std::rc::Rc;

type RegisterFile = Rc<dyn Fn(u8) -> u64>;

pub fn make_checked(value: u64) -> RegisterFile {
    let checked = check(value);
    Rc::new(move |_: u8| checked)
}

pub fn wrap(value: u64) -> RegisterFile {
    Rc::new(move |x: u8| {
        (*make_checked(value))(x)
    })
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.eta_forwarder_eliminations, 0);
        assert!(printed.contains("Rc::new(move |x: u8|"));
        assert!(printed.contains("(*make_checked(value))(x)"));
    }
}
