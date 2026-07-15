use rustlightast::*;

/// Result of the final conditional-expression cleanup pass.
#[derive(Debug, Clone, Default)]
pub struct IfCleanupAnalysis {
    /// Folded `if c { true } else { false }` or its negated counterpart.
    pub needless_bool_folds: usize,
}

/// Simplify conditional shapes that preserve evaluation of the condition.
pub fn cleanup_if(module: &mut RustModule) -> IfCleanupAnalysis {
    let mut analysis = IfCleanupAnalysis::default();
    cleanup_module(module, &mut analysis);
    analysis
}

fn cleanup_module(module: &mut RustModule, analysis: &mut IfCleanupAnalysis) {
    for item in &mut module.items {
        cleanup_item(item, analysis);
    }
}

fn cleanup_item(item: &mut Item, analysis: &mut IfCleanupAnalysis) {
    match item {
        Item::Function(function) => cleanup_block(&mut function.body, analysis),
        Item::Impl(impl_block) => {
            for item in &mut impl_block.items {
                match item {
                    ImplItem::Method(method) => cleanup_block(&mut method.body, analysis),
                    ImplItem::AssocConst(_, _, expr) => cleanup_expr(expr, analysis),
                    ImplItem::AssocType(_, _) => {}
                }
            }
        }
        Item::Const(const_def) => cleanup_expr(&mut const_def.value, analysis),
        Item::LazyStatic(lazy_static) => cleanup_block(&mut lazy_static.init, analysis),
        Item::Mod(inner) => cleanup_module(inner, analysis),
        Item::Raw(_)
        | Item::Struct(_)
        | Item::Enum(_)
        | Item::Union(_)
        | Item::TypeAlias(_)
        | Item::Use(_) => {}
    }
}

fn cleanup_block(block: &mut Block, analysis: &mut IfCleanupAnalysis) {
    for stmt in &mut block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    cleanup_expr(init, analysis);
                }
            }
            Statement::Expr(expr) => cleanup_expr(expr, analysis),
            Statement::Item(item) => cleanup_item(item, analysis),
            Statement::Continue | Statement::Break | Statement::Comment(_) => {}
        }
    }

    if let Some(tail) = &mut block.expr {
        cleanup_expr(tail, analysis);
    }
}

fn cleanup_expr(expr: &mut Expr, analysis: &mut IfCleanupAnalysis) {
    match expr {
        Expr::Call(callee, args) => {
            cleanup_expr(callee, analysis);
            for arg in args {
                cleanup_expr(arg, analysis);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            cleanup_expr(receiver, analysis);
            for arg in args {
                cleanup_expr(arg, analysis);
            }
        }
        Expr::Array(items) | Expr::Tuple(items) => {
            for item in items {
                cleanup_expr(item, analysis);
            }
        }
        Expr::Block(block) => cleanup_block(block, analysis),
        Expr::Loop(block) | Expr::Unsafe(block) => cleanup_block(block, analysis),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            cleanup_expr(condition, analysis);
            cleanup_block(then_branch, analysis);
            if let Some(else_branch) = else_branch {
                cleanup_block(else_branch, analysis);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            cleanup_expr(value, analysis);
            cleanup_block(then_branch, analysis);
            if let Some(else_branch) = else_branch {
                cleanup_block(else_branch, analysis);
            }
        }
        Expr::Match { expr, arms } => {
            cleanup_expr(expr, analysis);
            for arm in arms {
                if let Some(guard) = &mut arm.guard {
                    cleanup_expr(guard, analysis);
                }
                cleanup_block(&mut arm.body, analysis);
            }
        }
        Expr::Reference(inner, _, _)
        | Expr::UnaryOp(_, inner)
        | Expr::Await(inner)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Closure(_, inner, _) => cleanup_expr(inner, analysis),
        Expr::Index(base, index) | Expr::Assign(base, index) => {
            cleanup_expr(base, analysis);
            cleanup_expr(index, analysis);
        }
        Expr::BinaryOp(left, _, right) => {
            cleanup_expr(left, analysis);
            cleanup_expr(right, analysis);
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    cleanup_expr(closure, analysis);
                }
            }
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }

    let replacement = match expr {
        Expr::If {
            condition,
            then_branch,
            else_branch: Some(else_branch),
        } => match (bool_tail(then_branch), bool_tail(else_branch)) {
            (Some(true), Some(false)) => Some(condition.as_ref().clone()),
            (Some(false), Some(true)) => Some(Expr::UnaryOp(
                "!".to_string(),
                Box::new(Expr::Parenthesized(condition.clone())),
            )),
            _ => None,
        },
        _ => None,
    };

    if let Some(replacement) = replacement {
        *expr = replacement;
        analysis.needless_bool_folds += 1;
    }
}

fn bool_tail(block: &Block) -> Option<bool> {
    if !block.stmts.is_empty() {
        return None;
    }

    match block.expr.as_deref()? {
        Expr::Literal(Literal::Bool(value)) => Some(*value),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn bool_block(value: bool) -> Block {
        Block {
            stmts: Vec::new(),
            expr: Some(Box::new(Expr::Literal(Literal::Bool(value)))),
        }
    }

    fn bool_if(then_value: bool, else_value: bool) -> Expr {
        Expr::If {
            condition: Box::new(Expr::Ident("condition".to_string())),
            then_branch: bool_block(then_value),
            else_branch: Some(bool_block(else_value)),
        }
    }

    fn cleanup(expr: &mut Expr) -> IfCleanupAnalysis {
        let mut analysis = IfCleanupAnalysis::default();
        cleanup_expr(expr, &mut analysis);
        analysis
    }

    #[test]
    fn folds_true_false_to_condition() {
        let mut expr = bool_if(true, false);

        let analysis = cleanup(&mut expr);

        assert_eq!(analysis.needless_bool_folds, 1);
        assert!(matches!(expr, Expr::Ident(ref name) if name == "condition"));
    }

    #[test]
    fn folds_false_true_to_negated_condition() {
        let mut expr = bool_if(false, true);

        let analysis = cleanup(&mut expr);

        assert_eq!(analysis.needless_bool_folds, 1);
        assert!(matches!(
            expr,
            Expr::UnaryOp(ref op, ref inner)
                if op == "!"
                    && matches!(inner.as_ref(), Expr::Parenthesized(inner)
                        if matches!(inner.as_ref(), Expr::Ident(name) if name == "condition"))
        ));
    }

    #[test]
    fn keeps_branches_with_statements() {
        let mut expr = bool_if(true, false);
        let Expr::If { then_branch, .. } = &mut expr else {
            unreachable!()
        };
        then_branch
            .stmts
            .push(Statement::Comment("preserve evaluation".to_string()));

        let analysis = cleanup(&mut expr);

        assert_eq!(analysis.needless_bool_folds, 0);
        assert!(matches!(expr, Expr::If { .. }));
    }

    #[test]
    fn keeps_equal_boolean_branches() {
        let mut expr = bool_if(true, true);

        let analysis = cleanup(&mut expr);

        assert_eq!(analysis.needless_bool_folds, 0);
        assert!(matches!(expr, Expr::If { .. }));
    }
}
