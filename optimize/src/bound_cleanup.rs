use rustlightast::*;

/// Result of the conservative generated-bound cleanup pass.
#[derive(Debug, Clone, Default)]
pub struct BoundCleanupAnalysis {
    /// Number of redundant generated `Clone` bounds removed.
    pub removed_clone_bounds: usize,
    /// Number of redundant generated `'static` bounds removed.
    pub removed_static_bounds: usize,
    /// Number of free functions whose bounds were simplified.
    pub changed_functions: usize,
}

#[derive(Clone, Copy)]
enum BoundKind {
    Clone,
    Static,
}

/// Remove generated `Clone` and `'static` bounds only from structurally
/// bound-independent free functions.
///
/// The Isabelle backend deliberately puts both bounds on every generated type
/// parameter.  Later ownership passes can leave some of them redundant, but a
/// missing bound may also be required indirectly by a call or an escaping
/// closure.  This pass therefore handles only a small, proof-friendly subset:
/// signatures use the parameter directly (or through tuples/references), and
/// bodies contain only moves, destructuring, branches, and returns.  Calls,
/// opaque macros, closures, casts, generic wrapper types, and impl blocks are
/// conservative barriers.
pub fn cleanup_bounds(module: &mut RustModule) -> BoundCleanupAnalysis {
    let mut analysis = BoundCleanupAnalysis::default();
    cleanup_module(module, &mut analysis);
    analysis
}

fn cleanup_module(module: &mut RustModule, analysis: &mut BoundCleanupAnalysis) {
    for item in &mut module.items {
        match item {
            Item::Function(function) => cleanup_function(function, analysis),
            Item::Mod(inner) => cleanup_module(inner, analysis),
            // Impl bounds control the domain of a trait/inherent implementation
            // and are intentionally outside this conservative cleanup.
            Item::Raw(_)
            | Item::Struct(_)
            | Item::Enum(_)
            | Item::Union(_)
            | Item::Impl(_)
            | Item::Const(_)
            | Item::TypeAlias(_)
            | Item::Use(_)
            | Item::LazyStatic(_) => {}
        }
    }
}

fn cleanup_function(function: &mut FunctionDef, analysis: &mut BoundCleanupAnalysis) {
    let decisions = function
        .generics
        .iter()
        .map(|generic| {
            let can_remove_clone = generic.bounds.iter().any(|bound| bound == "Clone")
                && function_is_bound_independent(function, &generic.name, BoundKind::Clone);
            let can_remove_static = generic.bounds.iter().any(|bound| bound == "'static")
                && function_is_bound_independent(function, &generic.name, BoundKind::Static);
            (can_remove_clone, can_remove_static)
        })
        .collect::<Vec<_>>();

    let mut changed = false;
    for (generic, (remove_clone, remove_static)) in function.generics.iter_mut().zip(decisions) {
        if remove_clone {
            generic.bounds.retain(|bound| bound != "Clone");
            analysis.removed_clone_bounds += 1;
            changed = true;
        }
        if remove_static {
            generic.bounds.retain(|bound| bound != "'static");
            analysis.removed_static_bounds += 1;
            changed = true;
        }
    }

    if changed {
        analysis.changed_functions += 1;
    }
}

fn function_is_bound_independent(
    function: &FunctionDef,
    generic_name: &str,
    kind: BoundKind,
) -> bool {
    if function.asyncness || !function.attrs.is_empty() {
        return false;
    }

    if function
        .params
        .iter()
        .any(|param| !type_occurrence_is_neutral(&param.ty, generic_name))
        || !type_occurrence_is_neutral(&function.return_type, generic_name)
    {
        return false;
    }

    // A bound such as `B: Trait<A>` may make `A` well-formed indirectly even
    // when the value-level body is structural.  Keep both generated bounds in
    // that case instead of trying to interpret arbitrary trait syntax.
    if function.generics.iter().any(|generic| {
        generic.bounds.iter().any(|bound| {
            bound != "Clone" && bound != "'static" && bound_mentions_generic(bound, generic_name)
        })
    }) {
        return false;
    }

    block_is_bound_independent(&function.body, generic_name, kind)
}

fn type_occurrence_is_neutral(ty: &Type, generic_name: &str) -> bool {
    match ty {
        Type::Path(_) | Type::Unit | Type::Never => true,
        Type::Named(_) => true,
        // Generic wrappers may impose their own declaration-site bounds.  The
        // pass deliberately does not need a cross-crate type-definition model.
        Type::Generic(_, args) => !args
            .iter()
            .any(|arg| type_contains_generic(arg, generic_name)),
        // Callable trait objects have additional object-lifetime rules.  Keep
        // the generated bounds whenever this parameter occurs in one.
        Type::CallableTrait(callable) => !callable
            .args
            .iter()
            .chain(std::iter::once(callable.return_type.as_ref()))
            .any(|ty| type_contains_generic(ty, generic_name)),
        Type::Reference(inner, _, _) | Type::Slice(inner) | Type::Array(inner, _) => {
            type_occurrence_is_neutral(inner, generic_name)
        }
        Type::Tuple(types) => types
            .iter()
            .all(|ty| type_occurrence_is_neutral(ty, generic_name)),
    }
}

fn type_contains_generic(ty: &Type, generic_name: &str) -> bool {
    match ty {
        Type::Named(name) => name == generic_name,
        Type::Generic(_, args) | Type::Tuple(args) => args
            .iter()
            .any(|arg| type_contains_generic(arg, generic_name)),
        Type::CallableTrait(callable) => callable
            .args
            .iter()
            .chain(std::iter::once(callable.return_type.as_ref()))
            .any(|ty| type_contains_generic(ty, generic_name)),
        Type::Reference(inner, _, _) | Type::Slice(inner) | Type::Array(inner, _) => {
            type_contains_generic(inner, generic_name)
        }
        Type::Path(_) | Type::Unit | Type::Never => false,
    }
}

fn bound_mentions_generic(bound: &str, generic_name: &str) -> bool {
    bound
        .split(|ch: char| !ch.is_ascii_alphanumeric() && ch != '_')
        .any(|token| token == generic_name)
}

fn block_is_bound_independent(block: &Block, generic_name: &str, kind: BoundKind) -> bool {
    block.stmts.iter().all(|stmt| match stmt {
        Statement::Let(let_stmt) => {
            let_stmt
                .ty
                .as_ref()
                .is_none_or(|ty| type_occurrence_is_neutral(ty, generic_name))
                && let_stmt
                    .init
                    .as_ref()
                    .is_none_or(|expr| expr_is_bound_independent(expr, generic_name, kind))
        }
        Statement::Expr(expr) => expr_is_bound_independent(expr, generic_name, kind),
        Statement::Continue | Statement::Break | Statement::Comment(_) => true,
        Statement::Item(_) => false,
    }) && block
        .expr
        .as_deref()
        .is_none_or(|expr| expr_is_bound_independent(expr, generic_name, kind))
}

fn expr_is_bound_independent(expr: &Expr, generic_name: &str, kind: BoundKind) -> bool {
    match expr {
        Expr::Ident(_) | Expr::Literal(_) => true,
        Expr::Array(items) | Expr::Tuple(items) => items
            .iter()
            .all(|item| expr_is_bound_independent(item, generic_name, kind)),
        Expr::Block(block) => block_is_bound_independent(block, generic_name, kind),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            expr_is_bound_independent(condition, generic_name, kind)
                && block_is_bound_independent(then_branch, generic_name, kind)
                && else_branch
                    .as_ref()
                    .is_none_or(|block| block_is_bound_independent(block, generic_name, kind))
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            expr_is_bound_independent(value, generic_name, kind)
                && block_is_bound_independent(then_branch, generic_name, kind)
                && else_branch
                    .as_ref()
                    .is_none_or(|block| block_is_bound_independent(block, generic_name, kind))
        }
        Expr::Match { expr, arms } => {
            expr_is_bound_independent(expr, generic_name, kind)
                && arms.iter().all(|arm| {
                    arm.guard
                        .as_ref()
                        .is_none_or(|guard| expr_is_bound_independent(guard, generic_name, kind))
                        && block_is_bound_independent(&arm.body, generic_name, kind)
                })
        }
        Expr::Reference(inner, _, _) | Expr::Parenthesized(inner) => {
            expr_is_bound_independent(inner, generic_name, kind)
        }
        // Generated `.clone()` has no lifetime requirement of its own, so a
        // structural clone-only body may drop `'static` while retaining Clone.
        Expr::MethodCall(receiver, method, args)
            if matches!(kind, BoundKind::Static) && method == "clone" =>
        {
            expr_is_bound_independent(receiver, generic_name, kind)
                && args
                    .iter()
                    .all(|arg| expr_is_bound_independent(arg, generic_name, kind))
        }
        // Everything capable of invoking an unknown signature, hiding tokens,
        // or creating an escaping value is a conservative barrier.
        Expr::Path(_, _)
        | Expr::Macro(_)
        | Expr::Call(_, _)
        | Expr::MethodCall(_, _, _)
        | Expr::Loop(_)
        | Expr::Await(_)
        | Expr::Closure(_, _, _)
        | Expr::TypedClosure(_, _, _, _)
        | Expr::BuilderChain(_)
        | Expr::Unsafe(_)
        | Expr::UnaryOp(_, _)
        | Expr::BinaryOp(_, _, _)
        | Expr::Index(_, _)
        | Expr::Cast(_, _)
        | Expr::Assign(_, _) => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rustlight_parser::parse_rust_source;
    use rustlightast::RustCodeGenerator;

    fn cleanup(source: &str) -> (String, BoundCleanupAnalysis) {
        let mut module = parse_rust_source(source, "Test").expect("source should parse");
        let analysis = cleanup_bounds(&mut module);
        let mut generator = RustCodeGenerator::new();
        (generator.generate_module_code(&module), analysis)
    }

    #[test]
    fn removes_generated_bounds_from_identity_function() {
        let (printed, analysis) = cleanup(
            r#"
pub fn id<A>(x: A) -> A
where
    A: Clone + 'static,
{
    x
}
"#,
        );

        assert!(printed.contains("pub fn id<A>(x: A) -> A {"));
        assert!(!printed.contains("A: Clone"));
        assert!(!printed.contains("'static"));
        assert_eq!(analysis.removed_clone_bounds, 1);
        assert_eq!(analysis.removed_static_bounds, 1);
        assert_eq!(analysis.changed_functions, 1);
    }

    #[test]
    fn removes_generated_bounds_from_tuple_projection() {
        let (printed, analysis) = cleanup(
            r#"
pub fn snd<A, B>(x: (A, B)) -> B
where
    A: Clone + 'static,
    B: Clone + 'static,
{
    let (_, value) = x;
    value
}
"#,
        );

        assert!(printed.contains("pub fn snd<A, B>(x: (A, B)) -> B {"));
        assert_eq!(analysis.removed_clone_bounds, 2);
        assert_eq!(analysis.removed_static_bounds, 2);
    }

    #[test]
    fn keeps_clone_but_removes_static_from_direct_clone() {
        let (printed, analysis) = cleanup(
            r#"
pub fn duplicate<A>(x: A) -> A
where
    A: Clone + 'static,
{
    x.clone()
}
"#,
        );

        assert!(printed.contains("A: Clone"));
        assert!(!printed.contains("'static"));
        assert_eq!(analysis.removed_clone_bounds, 0);
        assert_eq!(analysis.removed_static_bounds, 1);
    }

    #[test]
    fn keeps_bounds_across_calls_and_closures() {
        let (called, called_analysis) = cleanup(
            r#"
pub fn caller<A>(x: A) -> A
where
    A: Clone + 'static,
{
    helper(x)
}
"#,
        );
        let (closed, closed_analysis) = cleanup(
            r#"
pub fn close<A>(x: A) -> A
where
    A: Clone + 'static,
{
    (move || x)()
}
"#,
        );

        assert!(called.contains("A: Clone + 'static"));
        assert!(closed.contains("A: Clone + 'static"));
        assert_eq!(called_analysis.changed_functions, 0);
        assert_eq!(closed_analysis.changed_functions, 0);
    }

    #[test]
    fn keeps_bounds_for_generic_wrappers_and_impls() {
        let (wrapped, wrapped_analysis) = cleanup(
            r#"
pub fn unwrap<A>(x: Wrapper<A>) -> Wrapper<A>
where
    A: Clone + 'static,
{
    x
}
"#,
        );
        let (implemented, implemented_analysis) = cleanup(
            r#"
impl<A: Clone + 'static> Trait for Wrapper<A> {
    fn value(x: A) -> A { x }
}
"#,
        );

        assert!(wrapped.contains("A: Clone + 'static"));
        assert!(implemented.contains("impl<A: Clone + 'static> Trait for Wrapper<A>"));
        assert_eq!(wrapped_analysis.changed_functions, 0);
        assert_eq!(implemented_analysis.changed_functions, 0);
    }

    #[test]
    fn preserves_non_generated_bounds() {
        let (printed, analysis) = cleanup(
            r#"
pub fn id<A>(x: A) -> A
where
    A: Clone + Equal + 'static,
{
    x
}
"#,
        );

        assert!(printed.contains("A: Equal"));
        assert!(!printed.contains("Clone"));
        assert!(!printed.contains("'static"));
        assert_eq!(analysis.removed_clone_bounds, 1);
        assert_eq!(analysis.removed_static_bounds, 1);
    }
}
