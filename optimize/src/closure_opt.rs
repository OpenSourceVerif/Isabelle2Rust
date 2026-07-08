use std::collections::HashMap;

use rustlightast::*;

/// Result of closure-local cleanup.
#[derive(Debug, Clone, Default)]
pub struct ClosureOptAnalysis {
    pub beta_reductions: usize,
}

/// Remove artifacts around immediately-created closures.
///
/// This pass is deliberately narrow.  It only beta-reduces the generated form
/// `(*Rc::new(move |p| body))(arg)`, where each parameter is read exactly once.
pub fn optimize_closure(module: &mut RustModule) -> ClosureOptAnalysis {
    let mut analysis = ClosureOptAnalysis::default();
    optimize_module(module, &mut analysis);
    analysis
}

fn optimize_module(module: &mut RustModule, analysis: &mut ClosureOptAnalysis) {
    for item in &mut module.items {
        optimize_item(item, analysis);
    }
}

fn optimize_item(item: &mut Item, analysis: &mut ClosureOptAnalysis) {
    match item {
        Item::Function(function) => optimize_block(&mut function.body, analysis),
        Item::Impl(impl_block) => {
            for item in &mut impl_block.items {
                match item {
                    ImplItem::Method(method) => optimize_block(&mut method.body, analysis),
                    ImplItem::AssocConst(_, _, expr) => optimize_expr(expr, analysis),
                    ImplItem::AssocType(_, _) => {}
                }
            }
        }
        Item::Const(const_def) => optimize_expr(&mut const_def.value, analysis),
        Item::LazyStatic(lazy_static) => optimize_block(&mut lazy_static.init, analysis),
        Item::Mod(inner) => optimize_module(inner, analysis),
        _ => {}
    }
}

fn optimize_block(block: &mut Block, analysis: &mut ClosureOptAnalysis) {
    for stmt in &mut block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    optimize_expr(init, analysis);
                }
            }
            Statement::Expr(expr) => optimize_expr(expr, analysis),
            Statement::Item(item) => optimize_item(item, analysis),
            Statement::Continue | Statement::Break | Statement::Comment(_) => {}
        }
    }

    if let Some(expr) = &mut block.expr {
        optimize_expr(expr, analysis);
    }
}

fn optimize_expr(expr: &mut Expr, analysis: &mut ClosureOptAnalysis) {
    match expr {
        Expr::Call(callee, args) => {
            optimize_expr(callee, analysis);
            for arg in &mut *args {
                optimize_expr(arg, analysis);
            }
            if let Some(reduced) = beta_reduce_immediate_closure(callee, args) {
                *expr = reduced;
                analysis.beta_reductions += 1;
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            optimize_expr(receiver, analysis);
            for arg in args {
                optimize_expr(arg, analysis);
            }
        }
        Expr::Tuple(items) => {
            for item in items {
                optimize_expr(item, analysis);
            }
        }
        Expr::Block(block) => {
            optimize_block(block, analysis);
        }
        Expr::Loop(block) | Expr::Unsafe(block) => {
            optimize_block(block, analysis);
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            optimize_expr(condition, analysis);
            optimize_block(then_branch, analysis);
            if let Some(else_branch) = else_branch {
                optimize_block(else_branch, analysis);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            optimize_expr(value, analysis);
            optimize_block(then_branch, analysis);
            if let Some(else_branch) = else_branch {
                optimize_block(else_branch, analysis);
            }
        }
        Expr::Match { expr, arms } => {
            optimize_expr(expr, analysis);
            for arm in arms {
                if let Some(guard) = &mut arm.guard {
                    optimize_expr(guard, analysis);
                }
                optimize_block(&mut arm.body, analysis);
            }
        }
        Expr::Reference(inner, _, _)
        | Expr::UnaryOp(_, inner)
        | Expr::Index(inner, _)
        | Expr::Assign(inner, _)
        | Expr::Await(inner)
        | Expr::Parenthesized(inner)
        | Expr::Closure(_, inner, _) => {
            optimize_expr(inner, analysis);
            match expr {
                Expr::Index(_, index) | Expr::Assign(_, index) => optimize_expr(index, analysis),
                _ => {}
            }
        }
        Expr::BinaryOp(left, _, right) => {
            optimize_expr(left, analysis);
            optimize_expr(right, analysis);
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    optimize_expr(closure, analysis);
                }
            }
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }
}

fn beta_reduce_immediate_closure(callee: &Expr, args: &[Expr]) -> Option<Expr> {
    let (params, body) = extract_immediate_move_closure(callee)?;
    if params.len() != args.len() {
        return None;
    }

    let mut subst = HashMap::new();
    for (param, arg) in params.iter().zip(args) {
        let name = closure_param_name(param);
        if !is_binding_ident(&name) || count_reads_in_expr(body, &name) != 1 || !is_simple_arg(arg)
        {
            return None;
        }
        subst.insert(name, arg.clone());
    }

    Some(simplify_reduced_body(subst_idents_in_expr(body, &subst)))
}

fn extract_immediate_move_closure(callee: &Expr) -> Option<(&[String], &Expr)> {
    let callee = strip_parens(callee);
    let Expr::UnaryOp(op, inner) = callee else {
        return None;
    };
    if op != "*" {
        return None;
    }

    let Expr::Call(rc_new, rc_args) = strip_parens(inner) else {
        return None;
    };
    if !is_rc_new(rc_new) || rc_args.len() != 1 {
        return None;
    }

    match strip_parens(&rc_args[0]) {
        Expr::Closure(params, body, true) => Some((params.as_slice(), body.as_ref())),
        _ => None,
    }
}

fn is_rc_new(expr: &Expr) -> bool {
    matches!(expr, Expr::Path(path, PathType::Namespace) if path.as_slice() == ["Rc", "new"])
}

fn simplify_reduced_body(expr: Expr) -> Expr {
    match expr {
        Expr::Block(Block { mut stmts, expr }) if stmts.is_empty() => {
            expr.map(|expr| *expr).unwrap_or(Expr::Block(Block {
                stmts: std::mem::take(&mut stmts),
                expr: None,
            }))
        }
        other => other,
    }
}

fn is_simple_arg(expr: &Expr) -> bool {
    match strip_parens(expr) {
        Expr::Ident(_) | Expr::Path(_, _) | Expr::Literal(_) => true,
        Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
            matches!(strip_parens(receiver), Expr::Ident(_) | Expr::Path(_, _))
        }
        Expr::UnaryOp(op, inner) if op == "*" => {
            matches!(strip_parens(inner), Expr::Ident(_) | Expr::Path(_, _))
        }
        _ => false,
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
        Expr::Tuple(items) => items
            .iter()
            .map(|item| count_reads_in_expr(item, name))
            .sum(),
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            count_reads_in_expr(left, name) + count_reads_in_expr(right, name)
        }
        Expr::UnaryOp(_, inner)
        | Expr::Reference(inner, _, _)
        | Expr::Parenthesized(inner)
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
        Expr::Closure(params, body, _) => {
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
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &let_stmt.init {
                    count += count_reads_in_expr(init, name);
                }
                if pattern_binds_name(&let_stmt.name, name) {
                    break;
                }
            }
            Statement::Expr(expr) => count += count_reads_in_expr(expr, name),
            Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {
            }
        }
    }

    if let Some(expr) = &block.expr {
        count += count_reads_in_expr(expr, name);
    }

    count
}

fn strip_parens(expr: &Expr) -> &Expr {
    match expr {
        Expr::Parenthesized(inner) => strip_parens(inner),
        other => other,
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
    use crate::parse_rust_source;

    fn optimize_and_print(source: &str) -> (ClosureOptAnalysis, String) {
        let mut module = parse_rust_source(source, "Test").expect("parse source");
        let analysis = optimize_closure(&mut module);
        let mut generator = RustCodeGenerator::new();
        (analysis, generator.generate_module_code(&module))
    }

    #[test]
    fn beta_reduces_immediate_rc_closure() {
        let source = r#"
use std::rc::Rc;

pub fn inc_abs(x: Int) -> Int {
    (*Rc::new(move |xa : Int| {
        plus_int(xa, one_int())
    }))(x)
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.beta_reductions, 1);
        assert!(printed.contains("plus_int(x, one_int())"));
        assert!(!printed.contains("Rc::new"));
    }

    #[test]
    fn keeps_multi_use_params() {
        let source = r#"
use std::rc::Rc;

pub fn dup(x: Int) -> (Int, Int) {
    (*Rc::new(move |xa : Int| {
        (xa, xa)
    }))(x)
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.beta_reductions, 0);
        assert!(printed.contains("Rc::new"));
    }

    #[test]
    fn keeps_shadowed_pattern_bindings_intact() {
        let source = r#"
use std::rc::Rc;

pub fn shadow(x: Int, y: Aoption) -> Int {
    (*Rc::new(move |xa : Int| {
        match y {
            Aoption::Somea(xa) => xa,
            Aoption::None => one_int(),
        }
    }))(x)
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.beta_reductions, 0);
        assert!(printed.contains("Rc::new"));
    }
}
