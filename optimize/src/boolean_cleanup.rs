use std::collections::HashSet;

use rustlightast::*;

/// Result of the final local Boolean-expression cleanup pass.
#[derive(Debug, Clone, Default)]
pub struct BooleanCleanupAnalysis {
    /// Folded `if c { true } else { false }` or its negated counterpart.
    pub conditional_folds: usize,
    /// Folded `false || e` or `e || false` to `e`.
    pub or_false_folds: usize,
    /// Folded `!(a == b)` to `a != b`.
    pub negated_equality_folds: usize,
    /// Hoisted block-valued `if` conditions into preceding local bindings.
    pub hoisted_block_conditions: usize,
}

/// Simplify local Boolean shapes while preserving operand evaluation.
pub fn cleanup_booleans(module: &mut RustModule) -> BooleanCleanupAnalysis {
    let mut analysis = BooleanCleanupAnalysis::default();
    cleanup_module(module, &mut analysis);
    analysis
}

fn cleanup_module(module: &mut RustModule, analysis: &mut BooleanCleanupAnalysis) {
    for item in &mut module.items {
        cleanup_item(item, analysis);
    }
}

fn cleanup_item(item: &mut Item, analysis: &mut BooleanCleanupAnalysis) {
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

fn cleanup_block(block: &mut Block, analysis: &mut BooleanCleanupAnalysis) {
    let mut used_names = HashSet::new();
    collect_identifiers_block(block, &mut used_names);
    let mut cleaned_stmts = Vec::with_capacity(block.stmts.len());

    for stmt in std::mem::take(&mut block.stmts) {
        match stmt {
            Statement::Let(mut let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    cleanup_expr(init, analysis);
                    if let Some(condition_binding) =
                        hoist_block_condition(init, &mut used_names, analysis)
                    {
                        cleaned_stmts.push(condition_binding);
                    }
                }
                cleaned_stmts.push(Statement::Let(let_stmt));
            }
            Statement::Expr(mut expr) => {
                cleanup_expr(&mut expr, analysis);
                if let Some(condition_binding) =
                    hoist_block_condition(&mut expr, &mut used_names, analysis)
                {
                    cleaned_stmts.push(condition_binding);
                }
                cleaned_stmts.push(Statement::Expr(expr));
            }
            Statement::Item(mut item) => {
                cleanup_item(&mut item, analysis);
                cleaned_stmts.push(Statement::Item(item));
            }
            other => cleaned_stmts.push(other),
        }
    }
    block.stmts = cleaned_stmts;

    if let Some(tail) = &mut block.expr {
        cleanup_expr(tail, analysis);
        if let Some(condition_binding) = hoist_block_condition(tail, &mut used_names, analysis) {
            block.stmts.push(condition_binding);
        }
    }
}

fn hoist_block_condition(
    expr: &mut Expr,
    used_names: &mut HashSet<String>,
    analysis: &mut BooleanCleanupAnalysis,
) -> Option<Statement> {
    let condition = direct_if_condition_mut(expr)?;
    if !is_block_expression(condition) {
        return None;
    }

    let name = fresh_condition_name(used_names);
    let init = strip_parenthesized_owned(*std::mem::replace(
        condition,
        Box::new(Expr::Ident(name.clone())),
    ));
    analysis.hoisted_block_conditions += 1;

    Some(Statement::Let(LetStmt {
        ifmut: false,
        name,
        ty: None,
        init: Some(init),
    }))
}

fn direct_if_condition_mut(expr: &mut Expr) -> Option<&mut Box<Expr>> {
    match expr {
        Expr::If { condition, .. } => Some(condition),
        Expr::Parenthesized(inner) => direct_if_condition_mut(inner),
        _ => None,
    }
}

fn is_block_expression(expr: &Expr) -> bool {
    match expr {
        Expr::Block(_) => true,
        Expr::Parenthesized(inner) => is_block_expression(inner),
        _ => false,
    }
}

fn strip_parenthesized_owned(mut expr: Expr) -> Expr {
    while let Expr::Parenthesized(inner) = expr {
        expr = *inner;
    }
    expr
}

fn fresh_condition_name(used_names: &mut HashSet<String>) -> String {
    if used_names.insert("condition".to_string()) {
        return "condition".to_string();
    }

    for index in 1.. {
        let candidate = format!("condition{index}");
        if used_names.insert(candidate.clone()) {
            return candidate;
        }
    }
    unreachable!()
}

fn collect_identifiers_block(block: &Block, names: &mut HashSet<String>) {
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &let_stmt.init {
                    collect_identifiers_expr(init, names);
                }
            }
            Statement::Expr(expr) => collect_identifiers_expr(expr, names),
            Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {
            }
        }
    }
    if let Some(tail) = &block.expr {
        collect_identifiers_expr(tail, names);
    }
}

fn collect_identifiers_expr(expr: &Expr, names: &mut HashSet<String>) {
    match expr {
        Expr::Call(callee, args) => {
            collect_identifiers_expr(callee, names);
            for arg in args {
                collect_identifiers_expr(arg, names);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            collect_identifiers_expr(receiver, names);
            for arg in args {
                collect_identifiers_expr(arg, names);
            }
        }
        Expr::Array(items) | Expr::Tuple(items) => {
            for item in items {
                collect_identifiers_expr(item, names);
            }
        }
        Expr::Block(block) => collect_identifiers_block(block, names),
        Expr::Loop(block) | Expr::Unsafe(block) => collect_identifiers_block(block, names),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            collect_identifiers_expr(condition, names);
            collect_identifiers_block(then_branch, names);
            if let Some(else_branch) = else_branch {
                collect_identifiers_block(else_branch, names);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            collect_identifiers_expr(value, names);
            collect_identifiers_block(then_branch, names);
            if let Some(else_branch) = else_branch {
                collect_identifiers_block(else_branch, names);
            }
        }
        Expr::Match { expr, arms } => {
            collect_identifiers_expr(expr, names);
            for arm in arms {
                if let Some(guard) = &arm.guard {
                    collect_identifiers_expr(guard, names);
                }
                collect_identifiers_block(&arm.body, names);
            }
        }
        Expr::Reference(inner, _, _)
        | Expr::UnaryOp(_, inner)
        | Expr::Await(inner)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Closure(_, inner, _)
        | Expr::TypedClosure(_, _, inner, _) => collect_identifiers_expr(inner, names),
        Expr::Index(base, index) | Expr::Assign(base, index) => {
            collect_identifiers_expr(base, names);
            collect_identifiers_expr(index, names);
        }
        Expr::BinaryOp(left, _, right) => {
            collect_identifiers_expr(left, names);
            collect_identifiers_expr(right, names);
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    collect_identifiers_expr(closure, names);
                }
            }
        }
        Expr::Ident(name) => {
            names.insert(name.clone());
        }
        Expr::Path(segments, _) => {
            names.extend(segments.iter().cloned());
        }
        Expr::Macro(_) | Expr::Literal(_) => {}
    }
}

fn cleanup_expr(expr: &mut Expr, analysis: &mut BooleanCleanupAnalysis) {
    cleanup_expr_with_context(expr, false, analysis);
}

fn cleanup_expr_with_context(
    expr: &mut Expr,
    parent_requires_inequality_parens: bool,
    analysis: &mut BooleanCleanupAnalysis,
) {
    match expr {
        Expr::Call(callee, args) => {
            cleanup_expr_with_context(callee, true, analysis);
            for arg in args {
                cleanup_expr(arg, analysis);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            cleanup_expr_with_context(receiver, true, analysis);
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
        Expr::Reference(inner, _, _) | Expr::Parenthesized(inner) => cleanup_expr(inner, analysis),
        Expr::UnaryOp(_, inner) | Expr::Await(inner) | Expr::Cast(inner, _) => {
            cleanup_expr_with_context(inner, true, analysis)
        }
        Expr::Closure(_, inner, _) | Expr::TypedClosure(_, _, inner, _) => {
            cleanup_expr(inner, analysis)
        }
        Expr::Index(base, index) => {
            cleanup_expr_with_context(base, true, analysis);
            cleanup_expr(index, analysis);
        }
        Expr::Assign(left, right) => {
            cleanup_expr_with_context(left, true, analysis);
            cleanup_expr(right, analysis);
        }
        Expr::BinaryOp(left, op, right) => {
            let child_requires_inequality_parens = !matches!(op.as_str(), "&&" | "||");
            cleanup_expr_with_context(left, child_requires_inequality_parens, analysis);
            cleanup_expr_with_context(right, child_requires_inequality_parens, analysis);
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

    while let Some((mut replacement, fold)) = boolean_replacement(expr) {
        if matches!(fold, BooleanFold::NegatedEquality) && parent_requires_inequality_parens {
            replacement = Expr::Parenthesized(Box::new(replacement));
        }

        *expr = replacement;
        match fold {
            BooleanFold::Conditional => analysis.conditional_folds += 1,
            BooleanFold::OrFalse => analysis.or_false_folds += 1,
            BooleanFold::NegatedEquality => analysis.negated_equality_folds += 1,
        }
    }
}

#[derive(Clone, Copy)]
enum BooleanFold {
    Conditional,
    OrFalse,
    NegatedEquality,
}

fn boolean_replacement(expr: &Expr) -> Option<(Expr, BooleanFold)> {
    match expr {
        Expr::If {
            condition,
            then_branch,
            else_branch: Some(else_branch),
        } => match (bool_tail(then_branch), bool_tail(else_branch)) {
            (Some(true), Some(false)) => {
                Some((condition.as_ref().clone(), BooleanFold::Conditional))
            }
            (Some(false), Some(true)) => Some((
                Expr::UnaryOp(
                    "!".to_string(),
                    Box::new(Expr::Parenthesized(condition.clone())),
                ),
                BooleanFold::Conditional,
            )),
            _ => None,
        },
        Expr::BinaryOp(left, op, right) if op == "||" && is_bool_literal(left, false) => {
            Some((right.as_ref().clone(), BooleanFold::OrFalse))
        }
        Expr::BinaryOp(left, op, right) if op == "||" && is_bool_literal(right, false) => {
            Some((left.as_ref().clone(), BooleanFold::OrFalse))
        }
        Expr::UnaryOp(op, inner) if op == "!" => {
            let Expr::BinaryOp(left, equality_op, right) = strip_parentheses(inner) else {
                return None;
            };
            if equality_op != "==" {
                return None;
            }
            Some((
                Expr::BinaryOp(left.clone(), "!=".to_string(), right.clone()),
                BooleanFold::NegatedEquality,
            ))
        }
        _ => None,
    }
}

fn strip_parentheses(mut expr: &Expr) -> &Expr {
    while let Expr::Parenthesized(inner) = expr {
        expr = inner;
    }
    expr
}

fn is_bool_literal(expr: &Expr, expected: bool) -> bool {
    matches!(
        strip_parentheses(expr),
        Expr::Literal(Literal::Bool(value)) if *value == expected
    )
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
    use crate::rustlight_parser::parse_rust_source;

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

    fn cleanup(expr: &mut Expr) -> BooleanCleanupAnalysis {
        let mut analysis = BooleanCleanupAnalysis::default();
        cleanup_expr(expr, &mut analysis);
        analysis
    }

    fn cleanup_source(source: &str) -> (String, BooleanCleanupAnalysis) {
        let mut module = parse_rust_source(source, "Test").expect("source should parse");
        let analysis = cleanup_booleans(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        syn::parse_file(&printed).expect("cleaned source should remain valid Rust syntax");
        (printed, analysis)
    }

    #[test]
    fn folds_true_false_to_condition() {
        let mut expr = bool_if(true, false);

        let analysis = cleanup(&mut expr);

        assert_eq!(analysis.conditional_folds, 1);
        assert!(matches!(expr, Expr::Ident(ref name) if name == "condition"));
    }

    #[test]
    fn folds_false_true_to_negated_condition() {
        let mut expr = bool_if(false, true);

        let analysis = cleanup(&mut expr);

        assert_eq!(analysis.conditional_folds, 1);
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

        assert_eq!(analysis.conditional_folds, 0);
        assert!(matches!(expr, Expr::If { .. }));
    }

    #[test]
    fn keeps_equal_boolean_branches() {
        let mut expr = bool_if(true, true);

        let analysis = cleanup(&mut expr);

        assert_eq!(analysis.conditional_folds, 0);
        assert!(matches!(expr, Expr::If { .. }));
    }

    #[test]
    fn folds_or_false_on_either_side() {
        let (printed, analysis) = cleanup_source(
            r#"
pub fn simplify(left: bool, right: bool) -> (bool, bool) {
    (false || left, right || false)
}
"#,
        );

        assert!(printed.contains("(left, right)"));
        assert_eq!(analysis.or_false_folds, 2);
    }

    #[test]
    fn folds_negated_equality() {
        let (printed, analysis) = cleanup_source(
            r#"
pub fn different(left: i32, right: i32) -> bool {
    !(left == right)
}
"#,
        );

        assert!(printed.contains("left != right"));
        assert!(!printed.contains("!(left == right)"));
        assert_eq!(analysis.negated_equality_folds, 1);
    }

    #[test]
    fn closes_rewrites_introduced_by_conditional_fold() {
        let (printed, analysis) = cleanup_source(
            r#"
pub fn different(left: i32, right: i32) -> bool {
    if left == right { false } else { true }
}
"#,
        );

        assert!(printed.contains("left != right"));
        assert_eq!(analysis.conditional_folds, 1);
        assert_eq!(analysis.negated_equality_folds, 1);
    }

    #[test]
    fn preserves_precedence_inside_another_comparison() {
        let (printed, analysis) = cleanup_source(
            r#"
pub fn compare(left: bool, right: bool, expected: bool) -> bool {
    !(left == right) == expected
}
"#,
        );

        assert!(printed.contains("(left != right) == expected"));
        assert_eq!(analysis.negated_equality_folds, 1);
    }

    #[test]
    fn keeps_or_true_because_folding_would_discard_left_evaluation() {
        let mut expr = Expr::BinaryOp(
            Box::new(Expr::Call(
                Box::new(Expr::Ident("effect".to_string())),
                Vec::new(),
            )),
            "||".to_string(),
            Box::new(Expr::Literal(Literal::Bool(true))),
        );

        let analysis = cleanup(&mut expr);

        assert_eq!(analysis.or_false_folds, 0);
        assert!(matches!(expr, Expr::BinaryOp(_, ref op, _) if op == "||"));
    }

    #[test]
    fn hoists_block_valued_if_condition() {
        let (printed, analysis) = cleanup_source(
            r#"
pub fn choose(x: (bool, bool), fallback: bool) -> bool {
    if {
        let (k, _) = x;
        k
    } {
        true
    } else {
        fallback
    }
}
"#,
        );

        assert_eq!(analysis.hoisted_block_conditions, 1);
        assert!(printed.contains("let condition = {"));
        assert!(printed.contains("if condition"));
        assert!(!printed.contains("if {"));
    }

    #[test]
    fn uses_fresh_name_when_condition_is_already_referenced() {
        let (printed, analysis) = cleanup_source(
            r#"
pub fn choose(condition: bool, x: (bool, bool)) -> bool {
    if {
        let (k, _) = x;
        k
    } {
        condition
    } else {
        false
    }
}
"#,
        );

        assert_eq!(analysis.hoisted_block_conditions, 1);
        assert!(printed.contains("let condition1 = {"));
        assert!(printed.contains("if condition1"));
        assert!(printed.contains("condition\n"));
    }
}
