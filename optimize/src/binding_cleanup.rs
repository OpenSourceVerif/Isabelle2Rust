use rustlightast::*;

/// Inline immutable, untyped bindings that are returned immediately.
pub fn cleanup_bindings(module: &mut RustModule) {
    collapse_trailing_let_returns_in_module(module);
}

fn collapse_trailing_let_returns_in_block(block: &mut Block) {
    for stmt in &mut block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    collapse_trailing_let_returns_in_expr(init);
                }
            }
            Statement::Expr(expr) => collapse_trailing_let_returns_in_expr(expr),
            Statement::Item(item) => collapse_trailing_let_returns_in_item(item),
            Statement::Continue | Statement::Break | Statement::Comment(_) => {}
        }
    }

    if let Some(tail) = &mut block.expr {
        collapse_trailing_let_returns_in_expr(tail);
    }
    collapse_trailing_let_return(block);
}

fn collapse_trailing_let_returns_in_module(module: &mut RustModule) {
    for item in &mut module.items {
        collapse_trailing_let_returns_in_item(item);
    }
}

fn collapse_trailing_let_returns_in_item(item: &mut Item) {
    match item {
        Item::Function(function) => collapse_trailing_let_returns_in_block(&mut function.body),
        Item::Impl(impl_block) => {
            for item in &mut impl_block.items {
                match item {
                    ImplItem::Method(method) => {
                        collapse_trailing_let_returns_in_block(&mut method.body);
                    }
                    ImplItem::AssocConst(_, _, expr) => {
                        collapse_trailing_let_returns_in_expr(expr);
                    }
                    ImplItem::AssocType(_, _) => {}
                }
            }
        }
        Item::Const(const_def) => collapse_trailing_let_returns_in_expr(&mut const_def.value),
        Item::LazyStatic(lazy_static) => {
            collapse_trailing_let_returns_in_block(&mut lazy_static.init);
        }
        Item::Mod(module) => {
            for item in &mut module.items {
                collapse_trailing_let_returns_in_item(item);
            }
        }
        Item::Raw(_)
        | Item::Struct(_)
        | Item::Enum(_)
        | Item::Union(_)
        | Item::TypeAlias(_)
        | Item::Use(_) => {}
    }
}

fn collapse_trailing_let_returns_in_expr(expr: &mut Expr) {
    match expr {
        Expr::Call(callee, args) => {
            collapse_trailing_let_returns_in_expr(callee);
            for arg in args {
                collapse_trailing_let_returns_in_expr(arg);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            collapse_trailing_let_returns_in_expr(receiver);
            for arg in args {
                collapse_trailing_let_returns_in_expr(arg);
            }
        }
        Expr::Array(items) | Expr::Tuple(items) => {
            for item in items {
                collapse_trailing_let_returns_in_expr(item);
            }
        }
        Expr::Block(block) => collapse_trailing_let_returns_in_block(block),
        Expr::Loop(block) | Expr::Unsafe(block) => collapse_trailing_let_returns_in_block(block),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            collapse_trailing_let_returns_in_expr(condition);
            collapse_trailing_let_returns_in_block(then_branch);
            if let Some(else_branch) = else_branch {
                collapse_trailing_let_returns_in_block(else_branch);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            collapse_trailing_let_returns_in_expr(value);
            collapse_trailing_let_returns_in_block(then_branch);
            if let Some(else_branch) = else_branch {
                collapse_trailing_let_returns_in_block(else_branch);
            }
        }
        Expr::Match { expr, arms } => {
            collapse_trailing_let_returns_in_expr(expr);
            for arm in arms {
                if let Some(guard) = &mut arm.guard {
                    collapse_trailing_let_returns_in_expr(guard);
                }
                collapse_trailing_let_returns_in_block(&mut arm.body);
            }
        }
        Expr::Reference(inner, _, _)
        | Expr::UnaryOp(_, inner)
        | Expr::Await(inner)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Closure(_, inner, _)
        | Expr::TypedClosure(_, _, inner, _) => collapse_trailing_let_returns_in_expr(inner),
        Expr::Index(base, index) | Expr::Assign(base, index) => {
            collapse_trailing_let_returns_in_expr(base);
            collapse_trailing_let_returns_in_expr(index);
        }
        Expr::BinaryOp(left, _, right) => {
            collapse_trailing_let_returns_in_expr(left);
            collapse_trailing_let_returns_in_expr(right);
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    collapse_trailing_let_returns_in_expr(closure);
                }
            }
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }
}

/// Inline immutable, untyped bindings that are returned immediately.  The
/// direct form is commonly exposed when M-LastUse turns `x.clone()` into `x`;
/// the clone form remains when borrow rewriting makes `x` a shared reference.
fn collapse_trailing_let_return(block: &mut Block) {
    while let Some(replacement) = trailing_let_return_replacement(block) {
        block.stmts.pop();
        block.expr = Some(Box::new(replacement));
    }
}

fn trailing_let_return_replacement(block: &Block) -> Option<Expr> {
    let Statement::Let(let_stmt) = block.stmts.last()? else {
        return None;
    };
    if let_stmt.ifmut || let_stmt.ty.is_some() || !is_binding_ident(&let_stmt.name) {
        return None;
    }

    let init = let_stmt.init.as_ref()?;
    match block.expr.as_deref()? {
        Expr::Ident(tail_name) if tail_name == &let_stmt.name => Some(init.clone()),
        Expr::MethodCall(receiver, method, args)
            if method == "clone"
                && args.is_empty()
                && matches!(receiver.as_ref(), Expr::Ident(name) if name == &let_stmt.name) =>
        {
            Some(Expr::MethodCall(
                Box::new(init.clone()),
                method.clone(),
                vec![],
            ))
        }
        _ => None,
    }
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
    fn binding_cleanup_collapses_borrowed_alias_before_clone() {
        let arm_body = Block {
            stmts: vec![let_stmt(
                "left",
                Expr::MethodCall(Box::new(ident("p0")), "as_ref".to_string(), vec![]),
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
        let mut module = module_with(function(ref_to(named("Tree")), body));

        cleanup_bindings(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Match { arms, .. }) = function.body.expr.as_deref() else {
            panic!("expected match")
        };
        assert!(arms[0].body.stmts.is_empty());
        assert!(matches!(
            arms[0].body.expr.as_deref(),
            Some(Expr::MethodCall(receiver, method, args))
                if method == "clone"
                    && args.is_empty()
                    && matches!(
                        receiver.as_ref(),
                        Expr::MethodCall(inner, inner_method, inner_args)
                            if inner_method == "as_ref"
                                && inner_args.is_empty()
                                && matches!(inner.as_ref(), Expr::Ident(name) if name == "p0")
                    )
        ));
    }

    #[test]
    fn binding_cleanup_collapses_trailing_alias_chain_to_fixed_point() {
        let mut block = Block {
            stmts: vec![let_stmt("x", ident("x0")), let_stmt("y", ident("x"))],
            expr: Some(Box::new(ident("y"))),
        };

        collapse_trailing_let_return(&mut block);

        assert!(block.stmts.is_empty());
        assert!(matches!(
            block.expr.as_deref(),
            Some(Expr::Ident(name)) if name == "x0"
        ));
    }

    #[test]
    fn trailing_let_cleanup_keeps_mut_typed_and_pattern_bindings() {
        let mut_binding = LetStmt {
            ifmut: true,
            name: "x".to_string(),
            ty: None,
            init: Some(ident("x0")),
        };
        let mut typed_binding = mut_binding.clone();
        typed_binding.ifmut = false;
        typed_binding.ty = Some(named("Int"));
        let mut pattern_binding = mut_binding.clone();
        pattern_binding.ifmut = false;
        pattern_binding.name = "(x, y)".to_string();

        for (binding, tail) in [
            (mut_binding, ident("x")),
            (typed_binding, ident("x")),
            (pattern_binding, ident("x")),
        ] {
            let mut block = Block {
                stmts: vec![Statement::Let(binding)],
                expr: Some(Box::new(tail)),
            };
            collapse_trailing_let_return(&mut block);
            assert_eq!(block.stmts.len(), 1);
        }
    }

    #[test]
    fn trailing_let_cleanup_reaches_module_level_consts() {
        let const_def = ConstDef {
            name: "VALUE".to_string(),
            ty: named("Int"),
            value: Expr::Block(Block {
                stmts: vec![let_stmt("x", Expr::Literal(Literal::Raw("1".to_string())))],
                expr: Some(Box::new(ident("x"))),
            }),
            vis: Visibility::Public,
            docs: vec![],
        };
        let mut module = RustModule {
            name: "Test".to_string(),
            docs: vec![],
            items: vec![Item::Const(const_def)],
            attrs: vec![],
            vis: Visibility::Public,
        };

        cleanup_bindings(&mut module);

        let Item::Const(const_def) = &module.items[0] else {
            panic!("expected const")
        };
        let Expr::Block(block) = &const_def.value else {
            panic!("expected block")
        };
        assert!(block.stmts.is_empty());
        assert!(matches!(
            block.expr.as_deref(),
            Some(Expr::Literal(Literal::Raw(value))) if value == "1"
        ));
    }
}
