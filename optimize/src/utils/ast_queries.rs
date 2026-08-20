use rustlightast::*;

use super::patterns::{closure_param_name, pattern_binds_name};

pub(crate) fn strip_parens(expr: &Expr) -> &Expr {
    match expr {
        Expr::Parenthesized(inner) => strip_parens(inner),
        other => other,
    }
}

#[derive(Clone, Copy)]
pub(crate) struct AstQueryOptions {
    pub respect_bindings: bool,
    pub visit_builder_chains: bool,
}

pub(crate) fn count_ident_reads_in_expr(
    expr: &Expr,
    name: &str,
    options: AstQueryOptions,
) -> usize {
    match expr {
        Expr::Ident(id) => usize::from(id == name),
        Expr::Path(path, PathType::Member) => {
            usize::from(path.first().is_some_and(|id| id == name))
        }
        Expr::MethodCall(receiver, _, args) => {
            count_ident_reads_in_expr(receiver, name, options)
                + args
                    .iter()
                    .map(|arg| count_ident_reads_in_expr(arg, name, options))
                    .sum::<usize>()
        }
        Expr::Call(callee, args) => {
            count_ident_reads_in_expr(callee, name, options)
                + args
                    .iter()
                    .map(|arg| count_ident_reads_in_expr(arg, name, options))
                    .sum::<usize>()
        }
        Expr::Block(block) => count_ident_reads_in_block(block, name, options),
        Expr::Array(items) | Expr::Tuple(items) => items
            .iter()
            .map(|item| count_ident_reads_in_expr(item, name, options))
            .sum(),
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            count_ident_reads_in_expr(left, name, options)
                + count_ident_reads_in_expr(right, name, options)
        }
        Expr::UnaryOp(_, inner)
        | Expr::Reference(inner, _, _)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Await(inner) => count_ident_reads_in_expr(inner, name, options),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            count_ident_reads_in_expr(condition, name, options)
                + count_ident_reads_in_block(then_branch, name, options)
                + else_branch.as_ref().map_or(0, |branch| {
                    count_ident_reads_in_block(branch, name, options)
                })
        }
        Expr::IfLet {
            pattern,
            value,
            then_branch,
            else_branch,
        } => {
            count_ident_reads_in_expr(value, name, options)
                + if options.respect_bindings && pattern_binds_name(pattern, name) {
                    0
                } else {
                    count_ident_reads_in_block(then_branch, name, options)
                }
                + else_branch.as_ref().map_or(0, |branch| {
                    count_ident_reads_in_block(branch, name, options)
                })
        }
        Expr::Match { expr, arms } => {
            count_ident_reads_in_expr(expr, name, options)
                + arms
                    .iter()
                    .map(|arm| {
                        if options.respect_bindings && pattern_binds_name(&arm.pattern, name) {
                            0
                        } else {
                            arm.guard
                                .as_ref()
                                .map_or(0, |guard| count_ident_reads_in_expr(guard, name, options))
                                + count_ident_reads_in_block(&arm.body, name, options)
                        }
                    })
                    .sum::<usize>()
        }
        Expr::Closure(params, body, _) | Expr::TypedClosure(params, _, body, _) => {
            if options.respect_bindings
                && params.iter().any(|param| closure_param_name(param) == name)
            {
                0
            } else {
                count_ident_reads_in_expr(body, name, options)
            }
        }
        Expr::Loop(block) | Expr::Unsafe(block) => count_ident_reads_in_block(block, name, options),
        Expr::BuilderChain(methods) if options.visit_builder_chains => methods
            .iter()
            .map(|method| match method {
                BuilderMethod::Spawn { closure, .. } => {
                    count_ident_reads_in_expr(closure, name, options)
                }
                BuilderMethod::Named(_) => 0,
            })
            .sum(),
        Expr::BuilderChain(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => 0,
    }
}

pub(crate) fn count_ident_reads_in_block(
    block: &Block,
    name: &str,
    options: AstQueryOptions,
) -> usize {
    let mut count = 0;
    let mut shadowed = false;
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &let_stmt.init {
                    count += count_ident_reads_in_expr(init, name, options);
                }
                if options.respect_bindings && pattern_binds_name(&let_stmt.name, name) {
                    shadowed = true;
                    break;
                }
            }
            Statement::Expr(expr) => count += count_ident_reads_in_expr(expr, name, options),
            Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {
            }
        }
    }
    if !shadowed {
        if let Some(expr) = &block.expr {
            count += count_ident_reads_in_expr(expr, name, options);
        }
    }
    count
}

pub(crate) fn count_bindings_in_expr(expr: &Expr, name: &str, visit_builder_chains: bool) -> usize {
    match expr {
        Expr::Closure(params, body, _) | Expr::TypedClosure(params, _, body, _) => {
            usize::from(params.iter().any(|param| closure_param_name(param) == name))
                + count_bindings_in_expr(body, name, visit_builder_chains)
        }
        Expr::Block(block) => count_bindings_in_block(block, name, visit_builder_chains),
        Expr::Loop(block) | Expr::Unsafe(block) => {
            count_bindings_in_block(block, name, visit_builder_chains)
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            count_bindings_in_expr(condition, name, visit_builder_chains)
                + count_bindings_in_block(then_branch, name, visit_builder_chains)
                + else_branch.as_ref().map_or(0, |branch| {
                    count_bindings_in_block(branch, name, visit_builder_chains)
                })
        }
        Expr::IfLet {
            pattern,
            value,
            then_branch,
            else_branch,
        } => {
            usize::from(pattern_binds_name(pattern, name))
                + count_bindings_in_expr(value, name, visit_builder_chains)
                + count_bindings_in_block(then_branch, name, visit_builder_chains)
                + else_branch.as_ref().map_or(0, |branch| {
                    count_bindings_in_block(branch, name, visit_builder_chains)
                })
        }
        Expr::Match { expr, arms } => {
            count_bindings_in_expr(expr, name, visit_builder_chains)
                + arms
                    .iter()
                    .map(|arm| {
                        usize::from(pattern_binds_name(&arm.pattern, name))
                            + arm.guard.as_ref().map_or(0, |guard| {
                                count_bindings_in_expr(guard, name, visit_builder_chains)
                            })
                            + count_bindings_in_block(&arm.body, name, visit_builder_chains)
                    })
                    .sum::<usize>()
        }
        Expr::Call(callee, args) => {
            count_bindings_in_expr(callee, name, visit_builder_chains)
                + args
                    .iter()
                    .map(|arg| count_bindings_in_expr(arg, name, visit_builder_chains))
                    .sum::<usize>()
        }
        Expr::MethodCall(receiver, _, args) => {
            count_bindings_in_expr(receiver, name, visit_builder_chains)
                + args
                    .iter()
                    .map(|arg| count_bindings_in_expr(arg, name, visit_builder_chains))
                    .sum::<usize>()
        }
        Expr::Array(items) | Expr::Tuple(items) => items
            .iter()
            .map(|item| count_bindings_in_expr(item, name, visit_builder_chains))
            .sum(),
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            count_bindings_in_expr(left, name, visit_builder_chains)
                + count_bindings_in_expr(right, name, visit_builder_chains)
        }
        Expr::UnaryOp(_, inner)
        | Expr::Reference(inner, _, _)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Await(inner) => count_bindings_in_expr(inner, name, visit_builder_chains),
        Expr::BuilderChain(methods) if visit_builder_chains => methods
            .iter()
            .map(|method| match method {
                BuilderMethod::Spawn { closure, .. } => {
                    count_bindings_in_expr(closure, name, visit_builder_chains)
                }
                BuilderMethod::Named(_) => 0,
            })
            .sum(),
        Expr::Ident(_)
        | Expr::Macro(_)
        | Expr::Path(_, _)
        | Expr::Literal(_)
        | Expr::BuilderChain(_) => 0,
    }
}

pub(crate) fn count_bindings_in_block(
    block: &Block,
    name: &str,
    visit_builder_chains: bool,
) -> usize {
    block
        .stmts
        .iter()
        .map(|stmt| match stmt {
            Statement::Let(let_stmt) => {
                usize::from(pattern_binds_name(&let_stmt.name, name))
                    + let_stmt.init.as_ref().map_or(0, |init| {
                        count_bindings_in_expr(init, name, visit_builder_chains)
                    })
            }
            Statement::Expr(expr) => count_bindings_in_expr(expr, name, visit_builder_chains),
            Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {
                0
            }
        })
        .sum::<usize>()
        + block.expr.as_ref().map_or(0, |expr| {
            count_bindings_in_expr(expr, name, visit_builder_chains)
        })
}
