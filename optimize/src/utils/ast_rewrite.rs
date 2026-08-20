use std::collections::HashMap;

use rustlightast::*;

use super::patterns::{closure_param_name, remove_pattern_bindings};

pub(crate) fn substitute_idents(expr: &Expr, substitutions: &HashMap<String, Expr>) -> Expr {
    match expr {
        Expr::Ident(name) => substitutions
            .get(name)
            .cloned()
            .unwrap_or_else(|| expr.clone()),
        Expr::Path(path, PathType::Member) if path.len() == 1 => substitutions
            .get(&path[0])
            .cloned()
            .unwrap_or_else(|| expr.clone()),
        Expr::MethodCall(receiver, method, args) => Expr::MethodCall(
            Box::new(substitute_idents(receiver, substitutions)),
            method.clone(),
            args.iter()
                .map(|arg| substitute_idents(arg, substitutions))
                .collect(),
        ),
        Expr::Call(callee, args) => Expr::Call(
            Box::new(substitute_idents(callee, substitutions)),
            args.iter()
                .map(|arg| substitute_idents(arg, substitutions))
                .collect(),
        ),
        Expr::Block(block) => Expr::Block(substitute_idents_in_block(block, substitutions)),
        Expr::Array(items) => Expr::Array(
            items
                .iter()
                .map(|item| substitute_idents(item, substitutions))
                .collect(),
        ),
        Expr::Tuple(items) => Expr::Tuple(
            items
                .iter()
                .map(|item| substitute_idents(item, substitutions))
                .collect(),
        ),
        Expr::BinaryOp(left, operator, right) => Expr::BinaryOp(
            Box::new(substitute_idents(left, substitutions)),
            operator.clone(),
            Box::new(substitute_idents(right, substitutions)),
        ),
        Expr::UnaryOp(operator, inner) => Expr::UnaryOp(
            operator.clone(),
            Box::new(substitute_idents(inner, substitutions)),
        ),
        Expr::Reference(inner, is_reference, mutable) => Expr::Reference(
            Box::new(substitute_idents(inner, substitutions)),
            *is_reference,
            *mutable,
        ),
        Expr::Index(base, index) => Expr::Index(
            Box::new(substitute_idents(base, substitutions)),
            Box::new(substitute_idents(index, substitutions)),
        ),
        Expr::Assign(left, right) => Expr::Assign(
            Box::new(substitute_idents(left, substitutions)),
            Box::new(substitute_idents(right, substitutions)),
        ),
        Expr::Parenthesized(inner) => {
            Expr::Parenthesized(Box::new(substitute_idents(inner, substitutions)))
        }
        Expr::Cast(inner, ty) => Expr::Cast(
            Box::new(substitute_idents(inner, substitutions)),
            ty.clone(),
        ),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => Expr::If {
            condition: Box::new(substitute_idents(condition, substitutions)),
            then_branch: substitute_idents_in_block(then_branch, substitutions),
            else_branch: else_branch
                .as_ref()
                .map(|branch| substitute_idents_in_block(branch, substitutions)),
        },
        Expr::IfLet {
            pattern,
            value,
            then_branch,
            else_branch,
        } => Expr::IfLet {
            pattern: pattern.clone(),
            value: Box::new(substitute_idents(value, substitutions)),
            then_branch: substitute_idents_in_block(
                then_branch,
                &without_pattern_bindings(substitutions, pattern),
            ),
            else_branch: else_branch
                .as_ref()
                .map(|branch| substitute_idents_in_block(branch, substitutions)),
        },
        Expr::Match { expr, arms } => Expr::Match {
            expr: Box::new(substitute_idents(expr, substitutions)),
            arms: arms
                .iter()
                .map(|arm| {
                    let arm_substitutions = without_pattern_bindings(substitutions, &arm.pattern);
                    MatchArm {
                        pattern: arm.pattern.clone(),
                        guard: arm
                            .guard
                            .as_ref()
                            .map(|guard| substitute_idents(guard, &arm_substitutions)),
                        body: substitute_idents_in_block(&arm.body, &arm_substitutions),
                    }
                })
                .collect(),
        },
        Expr::Closure(params, body, is_move) => {
            let mut inner = substitutions.clone();
            for param in params {
                inner.remove(&closure_param_name(param));
            }
            Expr::Closure(
                params.clone(),
                Box::new(substitute_idents(body, &inner)),
                *is_move,
            )
        }
        Expr::TypedClosure(params, return_type, body, is_move) => {
            let mut inner = substitutions.clone();
            for param in params {
                inner.remove(&closure_param_name(param));
            }
            Expr::TypedClosure(
                params.clone(),
                return_type.clone(),
                Box::new(substitute_idents(body, &inner)),
                *is_move,
            )
        }
        Expr::Loop(block) => Expr::Loop(Box::new(substitute_idents_in_block(block, substitutions))),
        Expr::Unsafe(block) => {
            Expr::Unsafe(Box::new(substitute_idents_in_block(block, substitutions)))
        }
        Expr::Await(inner) => Expr::Await(Box::new(substitute_idents(inner, substitutions))),
        Expr::BuilderChain(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {
            expr.clone()
        }
    }
}

fn substitute_idents_in_block(block: &Block, substitutions: &HashMap<String, Expr>) -> Block {
    let mut inner = substitutions.clone();
    let mut statements = Vec::with_capacity(block.stmts.len());

    for statement in &block.stmts {
        match statement {
            Statement::Let(let_stmt) => {
                let init = let_stmt
                    .init
                    .as_ref()
                    .map(|init| substitute_idents(init, &inner));
                remove_pattern_bindings(&let_stmt.name, &mut inner);
                statements.push(Statement::Let(LetStmt {
                    ifmut: let_stmt.ifmut,
                    name: let_stmt.name.clone(),
                    ty: let_stmt.ty.clone(),
                    init,
                }));
            }
            Statement::Expr(expr) => {
                statements.push(Statement::Expr(substitute_idents(expr, &inner)))
            }
            other => statements.push(other.clone()),
        }
    }

    Block {
        stmts: statements,
        expr: block
            .expr
            .as_ref()
            .map(|expr| Box::new(substitute_idents(expr, &inner))),
    }
}

fn without_pattern_bindings(
    substitutions: &HashMap<String, Expr>,
    pattern: &str,
) -> HashMap<String, Expr> {
    let mut inner = substitutions.clone();
    remove_pattern_bindings(pattern, &mut inner);
    inner
}

pub(crate) fn ensure_function_comment(function: &mut FunctionDef, comment: &str) {
    if !function.docs.iter().any(|doc| doc.trim() == comment) {
        function.docs.push(comment.to_string());
    }
}

pub(crate) fn ensure_item_comment(docs: &mut Vec<String>, comment: &str) {
    if !docs.iter().any(|doc| doc.trim() == comment) {
        docs.push(comment.to_string());
    }
}
