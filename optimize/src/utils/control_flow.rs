use rustlightast::*;

// Ownership passes model the existing expression-oriented fragment. Until
// they model loop back-edges and early exits, keep inputs with these nodes
// unchanged. Package-wide passes must check the whole input before changing
// any callee signature or generating specializations.
pub(crate) fn module_needs_control_flow_analysis(module: &RustModule) -> bool {
    module.items.iter().any(item_needs_control_flow_analysis)
}

fn item_needs_control_flow_analysis(item: &Item) -> bool {
    match item {
        Item::Function(f) => block_needs_control_flow_analysis(&f.body),
        Item::Mod(m) => module_needs_control_flow_analysis(m),
        Item::Const(c) => expr_needs_control_flow_analysis(&c.value),
        Item::LazyStatic(s) => block_needs_control_flow_analysis(&s.init),
        Item::Impl(i) => i.items.iter().any(|item| match item {
            ImplItem::Method(f) => block_needs_control_flow_analysis(&f.body),
            ImplItem::AssocConst(_, _, e) => expr_needs_control_flow_analysis(e),
            ImplItem::AssocType(_, _) => false,
        }),
        Item::Raw(_)
        | Item::Struct(_)
        | Item::Enum(_)
        | Item::Union(_)
        | Item::TypeAlias(_)
        | Item::Use(_) => false,
    }
}

pub(crate) fn block_needs_control_flow_analysis(block: &Block) -> bool {
    block.stmts.iter().any(|stmt| match stmt {
        Statement::Return(_) => true,
        Statement::Let(binding) => binding
            .init
            .as_ref()
            .is_some_and(expr_needs_control_flow_analysis),
        Statement::Expr(e) => expr_needs_control_flow_analysis(e),
        Statement::Item(item) => item_needs_control_flow_analysis(item),
        Statement::Continue | Statement::Break | Statement::Comment(_) => false,
    }) || block
        .expr
        .as_deref()
        .is_some_and(expr_needs_control_flow_analysis)
}

pub(crate) fn expr_needs_control_flow_analysis(expr: &Expr) -> bool {
    match expr {
        Expr::While { .. } | Expr::For { .. } => true,
        Expr::Block(b) => block_needs_control_flow_analysis(b),
        Expr::Loop(b) | Expr::Unsafe(b) => block_needs_control_flow_analysis(b),
        Expr::Call(f, args) | Expr::MethodCall(f, _, args) => {
            expr_needs_control_flow_analysis(f) || args.iter().any(expr_needs_control_flow_analysis)
        }
        Expr::Array(es) | Expr::Tuple(es) => es.iter().any(expr_needs_control_flow_analysis),
        Expr::Await(e)
        | Expr::Reference(e, _, _)
        | Expr::UnaryOp(_, e)
        | Expr::Parenthesized(e)
        | Expr::Cast(e, _)
        | Expr::Closure(_, e, _)
        | Expr::TypedClosure(_, _, e, _) => expr_needs_control_flow_analysis(e),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            expr_needs_control_flow_analysis(l) || expr_needs_control_flow_analysis(r)
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        }
        | Expr::IfLet {
            value: condition,
            then_branch,
            else_branch,
            ..
        } => {
            expr_needs_control_flow_analysis(condition)
                || block_needs_control_flow_analysis(then_branch)
                || else_branch
                    .as_ref()
                    .is_some_and(block_needs_control_flow_analysis)
        }
        Expr::Match { expr, arms } => {
            expr_needs_control_flow_analysis(expr)
                || arms.iter().any(|a| {
                    a.guard
                        .as_ref()
                        .is_some_and(expr_needs_control_flow_analysis)
                        || block_needs_control_flow_analysis(&a.body)
                })
        }
        Expr::BuilderChain(methods) => methods.iter().any(|method| match method {
            BuilderMethod::Spawn { closure, .. } => expr_needs_control_flow_analysis(closure),
            BuilderMethod::Named(_) => false,
        }),
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::utils::ast_queries::{count_ident_reads_in_expr, AstQueryOptions};
    use crate::utils::ast_rewrite::substitute_idents;
    use std::collections::{HashMap, HashSet};

    fn clone_x() -> Expr {
        Expr::MethodCall(Box::new(Expr::Ident("x".into())), "clone".into(), vec![])
    }

    #[test]
    fn ownership_passes_preserve_new_control_flow_and_package_interfaces() {
        let cases = [
            Statement::Return(Some(clone_x())),
            Statement::Return(None),
            Statement::Expr(Expr::While {
                condition: Box::new(Expr::Literal(Literal::Bool(false))),
                body: Block {
                    stmts: vec![Statement::Expr(clone_x())],
                    expr: None,
                },
            }),
            Statement::Expr(Expr::For {
                pattern: "entry".into(),
                iter: Box::new(Expr::Array(vec![clone_x()])),
                body: Block {
                    stmts: vec![Statement::Expr(clone_x())],
                    expr: None,
                },
            }),
        ];
        for statement in cases {
            let mut caller = crate::parse_rust_source(
                "pub fn keep(x: String) -> String { x.clone() }",
                "caller",
            )
            .unwrap();
            let Item::Function(function) = &mut caller.items[0] else {
                unreachable!()
            };
            function.body.stmts.push(statement);
            // The unrelated callee must also retain its interface when the
            // package contains a caller whose control flow is unsupported.
            let mut callee = crate::parse_rust_source(
                "pub fn inspect(x: String) -> usize { x.len() }",
                "callee",
            )
            .unwrap();
            let before = format!("{caller:?}{callee:?}");
            {
                let mut modules = [
                    (vec!["caller".into()], &mut caller),
                    (vec!["callee".into()], &mut callee),
                ];
                crate::optimize_copy_modules_with_paths(
                    &mut modules,
                    crate::CopyOptions::default(),
                );
                crate::optimize_borrow_modules_with_paths(&mut modules, &HashSet::new());
            }
            crate::optimize_mut(&mut caller);
            crate::optimize_last_use(&mut caller);
            assert_eq!(format!("{caller:?}{callee:?}"), before);
        }
    }

    #[test]
    fn boundary_finds_early_exits_in_nested_items_and_closures() {
        let mut module = crate::parse_rust_source("fn outer() { fn inner() {} }", "test").unwrap();
        let Item::Function(outer) = &mut module.items[0] else {
            unreachable!()
        };
        let Statement::Item(item) = &mut outer.body.stmts[0] else {
            unreachable!()
        };
        let Item::Function(inner) = item.as_mut() else {
            unreachable!()
        };
        inner.body.expr = Some(Box::new(Expr::Closure(
            vec![],
            Box::new(Expr::Block(Block {
                stmts: vec![Statement::Return(None)],
                expr: None,
            })),
            true,
        )));
        assert!(module_needs_control_flow_analysis(&module));
        let before = format!("{module:?}");
        crate::optimize_last_use(&mut module);
        assert_eq!(format!("{module:?}"), before);
    }

    #[test]
    fn for_traversal_respects_binding_scope_and_visits_return_values() {
        let expr = Expr::For {
            pattern: "x".into(),
            iter: Box::new(Expr::Ident("x".into())),
            body: Block {
                stmts: vec![Statement::Return(Some(Expr::Tuple(vec![
                    Expr::Ident("x".into()),
                    Expr::Ident("y".into()),
                ])))],
                expr: None,
            },
        };
        let options = AstQueryOptions {
            respect_bindings: true,
            visit_builder_chains: true,
        };
        assert_eq!(count_ident_reads_in_expr(&expr, "x", options), 1);
        assert_eq!(count_ident_reads_in_expr(&expr, "y", options), 1);
        let rewritten = substitute_idents(
            &expr,
            &HashMap::from([
                ("x".into(), Expr::Ident("outer".into())),
                ("y".into(), Expr::Ident("replacement".into())),
            ]),
        );
        let Expr::For { iter, body, .. } = rewritten else {
            unreachable!()
        };
        assert!(matches!(*iter, Expr::Ident(ref n) if n == "outer"));
        let Statement::Return(Some(Expr::Tuple(values))) = &body.stmts[0] else {
            unreachable!()
        };
        assert!(matches!(&values[0], Expr::Ident(n) if n == "x"));
        assert!(matches!(&values[1], Expr::Ident(n) if n == "replacement"));
    }

    #[test]
    fn cleanup_visits_while_conditions_for_iterators_and_return_operands() {
        fn redundant(value: &str) -> Expr {
            Expr::BinaryOp(
                Box::new(Expr::Literal(Literal::Bool(false))),
                "||".into(),
                Box::new(Expr::Ident(value.into())),
            )
        }
        let mut module = crate::parse_rust_source("fn test() {}", "test").unwrap();
        let Item::Function(function) = &mut module.items[0] else {
            unreachable!()
        };
        function.body.stmts = vec![Statement::Expr(Expr::While {
            condition: Box::new(redundant("condition")),
            body: Block {
                stmts: vec![Statement::Expr(Expr::For {
                    pattern: "entry".into(),
                    iter: Box::new(Expr::Array(vec![redundant("element")])),
                    body: Block {
                        stmts: vec![Statement::Return(Some(redundant("result")))],
                        expr: None,
                    },
                })],
                expr: None,
            },
        })];
        let analysis = crate::cleanup_booleans(&mut module);
        assert_eq!(analysis.or_false_folds, 3);
    }
}
