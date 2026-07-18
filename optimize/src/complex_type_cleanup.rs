use std::collections::{BTreeMap, HashMap, HashSet};

use rustlightast::*;

const ALIAS_PREFIX: &str = "I2rComplexTypeH";
const ALIAS_GENERIC_PREFIX: &str = "I2rT";
const CLIPPY_TYPE_COMPLEXITY_THRESHOLD: u64 = 250;

/// Summary of a complex-type cleanup run.
#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct ComplexTypeCleanupAnalysis {
    pub aliases_created: usize,
    pub rewritten_types: usize,
}

#[derive(Debug, Clone)]
struct Candidate {
    target: Type,
    generic_count: usize,
    public: bool,
}

#[derive(Debug, Clone)]
struct AliasSpec {
    name: String,
}

#[derive(Debug, Clone)]
struct NormalizedType {
    key: String,
    target: Type,
    arguments: Vec<Type>,
}

/// Extract complex type expressions into deterministic, module-local aliases.
///
/// The pass deliberately runs after the ownership and structural cleanup
/// passes. It therefore changes only type spelling, not inferred ownership or
/// expression structure.
pub fn cleanup_complex_types(module: &mut RustModule) -> ComplexTypeCleanupAnalysis {
    let mut analysis = ComplexTypeCleanupAnalysis::default();
    cleanup_module(module, &mut analysis);
    analysis
}

fn cleanup_module(module: &mut RustModule, analysis: &mut ComplexTypeCleanupAnalysis) {
    let mut candidates = BTreeMap::<String, Candidate>::new();
    for item in &module.items {
        if !matches!(item, Item::Mod(_)) {
            collect_item(item, &[], false, &mut candidates);
        }
    }

    if !candidates.is_empty() {
        let mut existing_names = module_item_names(module);
        let mut specs = BTreeMap::new();
        let mut aliases = Vec::with_capacity(candidates.len());

        for (key, candidate) in &candidates {
            let name = fresh_alias_name(key, &mut existing_names);
            specs.insert(key.clone(), AliasSpec { name: name.clone() });
            aliases.push(Item::TypeAlias(TypeAlias {
                name,
                target: candidate.target.clone(),
                generics: (0..candidate.generic_count)
                    .map(|index| GenericParam {
                        name: alias_generic_name(index),
                        bounds: Vec::new(),
                    })
                    .collect(),
                vis: if candidate.public {
                    Visibility::Public
                } else {
                    Visibility::Private
                },
                docs: Vec::new(),
            }));
        }

        for item in &mut module.items {
            if !matches!(item, Item::Mod(_)) {
                rewrite_item(item, &[], &specs, analysis);
            }
        }

        let insert_at = module
            .items
            .iter()
            .position(|item| !matches!(item, Item::Raw(_) | Item::Use(_)))
            .unwrap_or(module.items.len());
        analysis.aliases_created += aliases.len();
        module.items.splice(insert_at..insert_at, aliases);
    }

    for item in &mut module.items {
        if let Item::Mod(nested) = item {
            cleanup_module(nested, analysis);
        }
    }
}

fn collect_item(
    item: &Item,
    outer_generics: &[String],
    externally_visible: bool,
    candidates: &mut BTreeMap<String, Candidate>,
) {
    match item {
        Item::Struct(def) => {
            let generics = extend_scope(outer_generics, &def.generics);
            let public = externally_visible || is_exported(&def.vis);
            for field in &def.fields {
                collect_type_position(&field.ty, &generics, public, candidates);
            }
        }
        Item::Union(def) => {
            let generics = extend_scope(outer_generics, &def.generics);
            let public = externally_visible || is_exported(&def.vis);
            for field in &def.fields {
                collect_type_position(&field.ty, &generics, public, candidates);
            }
        }
        Item::Enum(def) => {
            let generics = extend_scope(outer_generics, &def.generics);
            let public = externally_visible || is_exported(&def.vis);
            for variant in &def.variants {
                if let Some(types) = &variant.data {
                    for ty in types {
                        collect_type_position(ty, &generics, public, candidates);
                    }
                }
            }
        }
        Item::Function(function) => collect_function(
            function,
            outer_generics,
            externally_visible || is_exported(&function.vis),
            candidates,
        ),
        Item::Impl(block) => {
            let impl_generics = extend_scope(outer_generics, &block.generics);
            let trait_visible = block.trait_impl.is_some();
            for item in &block.items {
                match item {
                    ImplItem::Method(function) => collect_function(
                        function,
                        &impl_generics,
                        trait_visible || is_exported(&function.vis),
                        candidates,
                    ),
                    ImplItem::AssocConst(_, ty, expr) => {
                        collect_type_position(ty, &impl_generics, trait_visible, candidates);
                        collect_expr(expr, &impl_generics, trait_visible, candidates);
                    }
                    ImplItem::AssocType(_, ty) => {
                        collect_type_position(ty, &impl_generics, trait_visible, candidates)
                    }
                }
            }
        }
        Item::Const(def) => {
            let public = externally_visible || is_exported(&def.vis);
            collect_type_position(&def.ty, outer_generics, public, candidates);
            collect_expr(&def.value, outer_generics, public, candidates);
        }
        // Existing aliases are intentional abstraction boundaries. Rewriting
        // their right-hand sides would also make a second run non-idempotent.
        Item::TypeAlias(_) => {}
        Item::LazyStatic(def) => {
            let public = externally_visible || is_exported(&def.vis);
            collect_type_position(&def.ty, outer_generics, public, candidates);
            collect_block(&def.init, outer_generics, public, candidates);
        }
        Item::Raw(_) | Item::Use(_) | Item::Mod(_) => {}
    }
}

fn collect_function(
    function: &FunctionDef,
    outer_generics: &[String],
    public: bool,
    candidates: &mut BTreeMap<String, Candidate>,
) {
    let generics = extend_scope(outer_generics, &function.generics);
    for param in &function.params {
        collect_type_position(&param.ty, &generics, public, candidates);
    }
    collect_type_position(&function.return_type, &generics, public, candidates);
    collect_block(&function.body, &generics, public, candidates);
}

fn collect_block(
    block: &Block,
    generics: &[String],
    public: bool,
    candidates: &mut BTreeMap<String, Candidate>,
) {
    for statement in &block.stmts {
        match statement {
            Statement::Let(binding) => {
                if let Some(ty) = &binding.ty {
                    collect_type_position(ty, generics, public, candidates);
                }
                if let Some(init) = &binding.init {
                    collect_expr(init, generics, public, candidates);
                }
            }
            Statement::Expr(expr) => collect_expr(expr, generics, public, candidates),
            Statement::Item(item) => collect_item(item, generics, public, candidates),
            Statement::Continue | Statement::Break | Statement::Comment(_) => {}
        }
    }
    if let Some(expr) = &block.expr {
        collect_expr(expr, generics, public, candidates);
    }
}

fn collect_expr(
    expr: &Expr,
    generics: &[String],
    public: bool,
    candidates: &mut BTreeMap<String, Candidate>,
) {
    match expr {
        Expr::Array(items) | Expr::Tuple(items) => {
            for item in items {
                collect_expr(item, generics, public, candidates);
            }
        }
        Expr::Call(callee, args) | Expr::MethodCall(callee, _, args) => {
            collect_expr(callee, generics, public, candidates);
            for arg in args {
                collect_expr(arg, generics, public, candidates);
            }
        }
        Expr::Block(block) => collect_block(block, generics, public, candidates),
        Expr::Loop(block) | Expr::Unsafe(block) => {
            collect_block(block, generics, public, candidates)
        }
        Expr::Await(inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::UnaryOp(_, inner) => collect_expr(inner, generics, public, candidates),
        Expr::Closure(params, body, _) => {
            for param in params {
                if let Some(ty) = &param.ty {
                    collect_type_position(ty, generics, public, candidates);
                }
            }
            collect_expr(body, generics, public, candidates);
        }
        Expr::TypedClosure(params, return_type, body, _) => {
            for param in params {
                if let Some(ty) = &param.ty {
                    collect_type_position(ty, generics, public, candidates);
                }
            }
            collect_type_position(return_type, generics, public, candidates);
            collect_expr(body, generics, public, candidates);
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                match method {
                    BuilderMethod::Named(_) => {}
                    BuilderMethod::Spawn { closure, .. } => {
                        collect_expr(closure, generics, public, candidates)
                    }
                }
            }
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
            collect_expr(condition, generics, public, candidates);
            collect_block(then_branch, generics, public, candidates);
            if let Some(else_branch) = else_branch {
                collect_block(else_branch, generics, public, candidates);
            }
        }
        Expr::Match { expr, arms } => {
            collect_expr(expr, generics, public, candidates);
            for arm in arms {
                if let Some(guard) = &arm.guard {
                    collect_expr(guard, generics, public, candidates);
                }
                collect_block(&arm.body, generics, public, candidates);
            }
        }
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            collect_expr(left, generics, public, candidates);
            collect_expr(right, generics, public, candidates);
        }
        Expr::Cast(inner, ty) => {
            collect_expr(inner, generics, public, candidates);
            collect_type_position(ty, generics, public, candidates);
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }
}

fn collect_type_position(
    ty: &Type,
    generics: &[String],
    public: bool,
    candidates: &mut BTreeMap<String, Candidate>,
) {
    if is_generated_alias(ty) {
        return;
    }

    if !matches!(ty, Type::Reference(_, _, _)) && should_alias(ty) {
        let normalized = normalize_type(ty, generics);
        candidates
            .entry(normalized.key)
            .and_modify(|candidate| candidate.public |= public)
            .or_insert(Candidate {
                target: normalized.target,
                generic_count: normalized.arguments.len(),
                public,
            });
        return;
    }

    for child in type_children(ty) {
        collect_type_position(child, generics, public, candidates);
    }
}

fn rewrite_item(
    item: &mut Item,
    outer_generics: &[String],
    specs: &BTreeMap<String, AliasSpec>,
    analysis: &mut ComplexTypeCleanupAnalysis,
) {
    match item {
        Item::Struct(def) => {
            let generics = extend_scope(outer_generics, &def.generics);
            for field in &mut def.fields {
                rewrite_type_position(&mut field.ty, &generics, specs, analysis);
            }
        }
        Item::Union(def) => {
            let generics = extend_scope(outer_generics, &def.generics);
            for field in &mut def.fields {
                rewrite_type_position(&mut field.ty, &generics, specs, analysis);
            }
        }
        Item::Enum(def) => {
            let generics = extend_scope(outer_generics, &def.generics);
            for variant in &mut def.variants {
                if let Some(types) = &mut variant.data {
                    for ty in types {
                        rewrite_type_position(ty, &generics, specs, analysis);
                    }
                }
            }
        }
        Item::Function(function) => rewrite_function(function, outer_generics, specs, analysis),
        Item::Impl(block) => {
            let generics = extend_scope(outer_generics, &block.generics);
            for item in &mut block.items {
                match item {
                    ImplItem::Method(function) => {
                        rewrite_function(function, &generics, specs, analysis)
                    }
                    ImplItem::AssocConst(_, ty, expr) => {
                        rewrite_type_position(ty, &generics, specs, analysis);
                        rewrite_expr(expr, &generics, specs, analysis);
                    }
                    ImplItem::AssocType(_, ty) => {
                        rewrite_type_position(ty, &generics, specs, analysis)
                    }
                }
            }
        }
        Item::Const(def) => {
            rewrite_type_position(&mut def.ty, outer_generics, specs, analysis);
            rewrite_expr(&mut def.value, outer_generics, specs, analysis);
        }
        Item::LazyStatic(def) => {
            rewrite_type_position(&mut def.ty, outer_generics, specs, analysis);
            rewrite_block(&mut def.init, outer_generics, specs, analysis);
        }
        Item::TypeAlias(_) | Item::Raw(_) | Item::Use(_) | Item::Mod(_) => {}
    }
}

fn rewrite_function(
    function: &mut FunctionDef,
    outer_generics: &[String],
    specs: &BTreeMap<String, AliasSpec>,
    analysis: &mut ComplexTypeCleanupAnalysis,
) {
    let generics = extend_scope(outer_generics, &function.generics);
    for param in &mut function.params {
        rewrite_type_position(&mut param.ty, &generics, specs, analysis);
    }
    rewrite_type_position(&mut function.return_type, &generics, specs, analysis);
    rewrite_block(&mut function.body, &generics, specs, analysis);
}

fn rewrite_block(
    block: &mut Block,
    generics: &[String],
    specs: &BTreeMap<String, AliasSpec>,
    analysis: &mut ComplexTypeCleanupAnalysis,
) {
    for statement in &mut block.stmts {
        match statement {
            Statement::Let(binding) => {
                if let Some(ty) = &mut binding.ty {
                    rewrite_type_position(ty, generics, specs, analysis);
                }
                if let Some(init) = &mut binding.init {
                    rewrite_expr(init, generics, specs, analysis);
                }
            }
            Statement::Expr(expr) => rewrite_expr(expr, generics, specs, analysis),
            Statement::Item(item) => rewrite_item(item, generics, specs, analysis),
            Statement::Continue | Statement::Break | Statement::Comment(_) => {}
        }
    }
    if let Some(expr) = &mut block.expr {
        rewrite_expr(expr, generics, specs, analysis);
    }
}

fn rewrite_expr(
    expr: &mut Expr,
    generics: &[String],
    specs: &BTreeMap<String, AliasSpec>,
    analysis: &mut ComplexTypeCleanupAnalysis,
) {
    match expr {
        Expr::Array(items) | Expr::Tuple(items) => {
            for item in items {
                rewrite_expr(item, generics, specs, analysis);
            }
        }
        Expr::Call(callee, args) | Expr::MethodCall(callee, _, args) => {
            rewrite_expr(callee, generics, specs, analysis);
            for arg in args {
                rewrite_expr(arg, generics, specs, analysis);
            }
        }
        Expr::Block(block) => rewrite_block(block, generics, specs, analysis),
        Expr::Loop(block) | Expr::Unsafe(block) => rewrite_block(block, generics, specs, analysis),
        Expr::Await(inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::UnaryOp(_, inner) => rewrite_expr(inner, generics, specs, analysis),
        Expr::Closure(params, body, _) => {
            for param in params {
                if let Some(ty) = &mut param.ty {
                    rewrite_type_position(ty, generics, specs, analysis);
                }
            }
            rewrite_expr(body, generics, specs, analysis);
        }
        Expr::TypedClosure(params, return_type, body, _) => {
            for param in params {
                if let Some(ty) = &mut param.ty {
                    rewrite_type_position(ty, generics, specs, analysis);
                }
            }
            rewrite_type_position(return_type, generics, specs, analysis);
            rewrite_expr(body, generics, specs, analysis);
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                match method {
                    BuilderMethod::Named(_) => {}
                    BuilderMethod::Spawn { closure, .. } => {
                        rewrite_expr(closure, generics, specs, analysis)
                    }
                }
            }
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
            rewrite_expr(condition, generics, specs, analysis);
            rewrite_block(then_branch, generics, specs, analysis);
            if let Some(else_branch) = else_branch {
                rewrite_block(else_branch, generics, specs, analysis);
            }
        }
        Expr::Match { expr, arms } => {
            rewrite_expr(expr, generics, specs, analysis);
            for arm in arms {
                if let Some(guard) = &mut arm.guard {
                    rewrite_expr(guard, generics, specs, analysis);
                }
                rewrite_block(&mut arm.body, generics, specs, analysis);
            }
        }
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            rewrite_expr(left, generics, specs, analysis);
            rewrite_expr(right, generics, specs, analysis);
        }
        Expr::Cast(inner, ty) => {
            rewrite_expr(inner, generics, specs, analysis);
            rewrite_type_position(ty, generics, specs, analysis);
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }
}

fn rewrite_type_position(
    ty: &mut Type,
    generics: &[String],
    specs: &BTreeMap<String, AliasSpec>,
    analysis: &mut ComplexTypeCleanupAnalysis,
) {
    if is_generated_alias(ty) {
        return;
    }

    if !matches!(ty, Type::Reference(_, _, _)) && should_alias(ty) {
        let normalized = normalize_type(ty, generics);
        if let Some(spec) = specs.get(&normalized.key) {
            *ty = if normalized.arguments.is_empty() {
                Type::Named(spec.name.clone())
            } else {
                Type::Generic(spec.name.clone(), normalized.arguments)
            };
            analysis.rewritten_types += 1;
            return;
        }
    }

    match ty {
        Type::Generic(_, args) | Type::Tuple(args) => {
            for arg in args {
                rewrite_type_position(arg, generics, specs, analysis);
            }
        }
        Type::CallableTrait(callable) => {
            for arg in &mut callable.args {
                rewrite_type_position(arg, generics, specs, analysis);
            }
            rewrite_type_position(&mut callable.return_type, generics, specs, analysis);
        }
        Type::Reference(inner, _, _) | Type::Slice(inner) | Type::Array(inner, _) => {
            rewrite_type_position(inner, generics, specs, analysis)
        }
        Type::Path(_) | Type::Named(_) | Type::Unit | Type::Never => {}
    }
}

fn should_alias(ty: &Type) -> bool {
    !contains_impl_callable(ty) && clippy_type_complexity(ty, 1) > CLIPPY_TYPE_COMPLEXITY_THRESHOLD
}

/// Mirrors Clippy's public `type_complexity` scoring model closely enough for
/// the RustLightAST type fragment. Keeping the same default threshold avoids
/// generating aliases for types that Clippy already considers readable.
fn clippy_type_complexity(ty: &Type, nest: u64) -> u64 {
    match ty {
        Type::Path(_) | Type::Named(_) | Type::Unit => 10 * nest,
        Type::Never => 0,
        Type::Generic(_, args) => {
            10 * nest
                + args
                    .iter()
                    .map(|arg| clippy_type_complexity(arg, nest + 1))
                    .sum::<u64>()
        }
        Type::CallableTrait(callable) => {
            let own_score = match callable.qualifier {
                CallableTraitQualifier::Dyn => 20 * nest,
                CallableTraitQualifier::Impl => 0,
            };
            own_score
                // Rust HIR represents the parenthesized `Fn(A, B)` inputs as
                // a tuple type, which Clippy visits before the input types.
                + 10 * nest
                + callable
                    .args
                    .iter()
                    .map(|arg| clippy_type_complexity(arg, nest + 1))
                    .sum::<u64>()
                + clippy_type_complexity(&callable.return_type, nest)
        }
        Type::Reference(inner, _, _) => 1 + clippy_type_complexity(inner, nest),
        Type::Tuple(types) => {
            10 * nest
                + types
                    .iter()
                    .map(|ty| clippy_type_complexity(ty, nest + 1))
                    .sum::<u64>()
        }
        Type::Slice(inner) | Type::Array(inner, _) => {
            10 * nest + clippy_type_complexity(inner, nest + 1)
        }
    }
}

fn contains_impl_callable(ty: &Type) -> bool {
    match ty {
        Type::CallableTrait(callable) => {
            matches!(callable.qualifier, CallableTraitQualifier::Impl)
                || callable.args.iter().any(contains_impl_callable)
                || contains_impl_callable(&callable.return_type)
        }
        Type::Generic(_, args) | Type::Tuple(args) => args.iter().any(contains_impl_callable),
        Type::Reference(inner, _, _) | Type::Slice(inner) | Type::Array(inner, _) => {
            contains_impl_callable(inner)
        }
        Type::Path(_) | Type::Named(_) | Type::Unit | Type::Never => false,
    }
}

fn normalize_type(ty: &Type, generics: &[String]) -> NormalizedType {
    let generic_scope = generics.iter().map(String::as_str).collect::<HashSet<_>>();
    let mut generic_indexes = HashMap::<String, usize>::new();
    let mut arguments = Vec::new();
    let (key, target) =
        normalize_type_inner(ty, &generic_scope, &mut generic_indexes, &mut arguments);
    NormalizedType {
        key,
        target,
        arguments,
    }
}

fn normalize_type_inner(
    ty: &Type,
    generic_scope: &HashSet<&str>,
    generic_indexes: &mut HashMap<String, usize>,
    arguments: &mut Vec<Type>,
) -> (String, Type) {
    match ty {
        Type::Named(name) if generic_scope.contains(name.as_str()) => {
            let index = if let Some(index) = generic_indexes.get(name) {
                *index
            } else {
                let index = generic_indexes.len();
                generic_indexes.insert(name.clone(), index);
                arguments.push(Type::Named(name.clone()));
                index
            };
            (format!("V{index}"), Type::Named(alias_generic_name(index)))
        }
        Type::Named(name) => (atom_key("N", name), Type::Named(name.clone())),
        Type::Path(path) => {
            let key = path
                .iter()
                .map(|part| atom_key("", part))
                .collect::<Vec<_>>()
                .join(":");
            (format!("P[{key}]"), Type::Path(path.clone()))
        }
        Type::Generic(name, args) => {
            let normalized = args
                .iter()
                .map(|arg| normalize_type_inner(arg, generic_scope, generic_indexes, arguments))
                .collect::<Vec<_>>();
            let key = normalized
                .iter()
                .map(|(key, _)| key.as_str())
                .collect::<Vec<_>>()
                .join(",");
            (
                format!("G{}[{key}]", atom_key("", name)),
                Type::Generic(
                    name.clone(),
                    normalized.into_iter().map(|(_, ty)| ty).collect(),
                ),
            )
        }
        Type::CallableTrait(callable) => {
            let normalized_args = callable
                .args
                .iter()
                .map(|arg| normalize_type_inner(arg, generic_scope, generic_indexes, arguments))
                .collect::<Vec<_>>();
            let (return_key, return_type) = normalize_type_inner(
                &callable.return_type,
                generic_scope,
                generic_indexes,
                arguments,
            );
            let arg_key = normalized_args
                .iter()
                .map(|(key, _)| key.as_str())
                .collect::<Vec<_>>()
                .join(",");
            let qualifier = match callable.qualifier {
                CallableTraitQualifier::Dyn => "D",
                CallableTraitQualifier::Impl => "I",
            };
            (
                format!(
                    "C{qualifier}{}[{arg_key}]->{return_key}",
                    atom_key("", &callable.trait_name)
                ),
                Type::CallableTrait(CallableTraitType {
                    qualifier: callable.qualifier.clone(),
                    trait_name: callable.trait_name.clone(),
                    args: normalized_args.into_iter().map(|(_, ty)| ty).collect(),
                    return_type: Box::new(return_type),
                }),
            )
        }
        Type::Reference(inner, is_reference, mutable) => {
            let (key, inner) =
                normalize_type_inner(inner, generic_scope, generic_indexes, arguments);
            (
                format!(
                    "R{}{}[{key}]",
                    usize::from(*is_reference),
                    usize::from(*mutable)
                ),
                Type::Reference(Box::new(inner), *is_reference, *mutable),
            )
        }
        Type::Tuple(types) => {
            let normalized = types
                .iter()
                .map(|ty| normalize_type_inner(ty, generic_scope, generic_indexes, arguments))
                .collect::<Vec<_>>();
            let key = normalized
                .iter()
                .map(|(key, _)| key.as_str())
                .collect::<Vec<_>>()
                .join(",");
            (
                format!("T[{key}]"),
                Type::Tuple(normalized.into_iter().map(|(_, ty)| ty).collect()),
            )
        }
        Type::Slice(inner) => {
            let (key, inner) =
                normalize_type_inner(inner, generic_scope, generic_indexes, arguments);
            (format!("S[{key}]"), Type::Slice(Box::new(inner)))
        }
        Type::Array(inner, size) => {
            let (key, inner) =
                normalize_type_inner(inner, generic_scope, generic_indexes, arguments);
            (
                format!("A{size}[{key}]"),
                Type::Array(Box::new(inner), *size),
            )
        }
        Type::Unit => ("U".to_string(), Type::Unit),
        Type::Never => ("!".to_string(), Type::Never),
    }
}

fn type_children(ty: &Type) -> Vec<&Type> {
    match ty {
        Type::Generic(_, args) | Type::Tuple(args) => args.iter().collect(),
        Type::CallableTrait(callable) => callable
            .args
            .iter()
            .chain(std::iter::once(callable.return_type.as_ref()))
            .collect(),
        Type::Reference(inner, _, _) | Type::Slice(inner) | Type::Array(inner, _) => {
            vec![inner.as_ref()]
        }
        Type::Path(_) | Type::Named(_) | Type::Unit | Type::Never => Vec::new(),
    }
}

fn extend_scope(outer: &[String], generics: &[GenericParam]) -> Vec<String> {
    let mut scope = outer.to_vec();
    scope.extend(generics.iter().map(|generic| generic.name.clone()));
    scope
}

fn is_exported(vis: &Visibility) -> bool {
    matches!(vis, Visibility::Public | Visibility::Restricted(_))
}

fn is_generated_alias(ty: &Type) -> bool {
    matches!(ty, Type::Named(name) | Type::Generic(name, _) if name.starts_with(ALIAS_PREFIX))
}

fn module_item_names(module: &RustModule) -> HashSet<String> {
    module
        .items
        .iter()
        .filter_map(|item| match item {
            Item::Struct(def) => Some(def.name.clone()),
            Item::Union(def) => Some(def.name.clone()),
            Item::Enum(def) => Some(def.name.clone()),
            Item::Function(def) => Some(def.name.clone()),
            Item::Const(def) => Some(def.name.clone()),
            Item::TypeAlias(def) => Some(def.name.clone()),
            Item::Mod(def) => Some(def.name.clone()),
            Item::LazyStatic(def) => Some(def.name.clone()),
            Item::Raw(_) | Item::Impl(_) | Item::Use(_) => None,
        })
        .collect()
}

fn fresh_alias_name(key: &str, existing_names: &mut HashSet<String>) -> String {
    let base = format!("{ALIAS_PREFIX}{:016X}", fnv1a64(key.as_bytes()));
    if existing_names.insert(base.clone()) {
        return base;
    }

    let mut suffix = 2usize;
    loop {
        let candidate = format!("{base}N{suffix}");
        if existing_names.insert(candidate.clone()) {
            return candidate;
        }
        suffix += 1;
    }
}

fn fnv1a64(bytes: &[u8]) -> u64 {
    let mut hash = 0xcbf29ce484222325u64;
    for byte in bytes {
        hash ^= u64::from(*byte);
        hash = hash.wrapping_mul(0x100000001b3);
    }
    hash
}

fn alias_generic_name(index: usize) -> String {
    format!("{ALIAS_GENERIC_PREFIX}{index}")
}

fn atom_key(prefix: &str, value: &str) -> String {
    format!("{prefix}{}:{value}", value.len())
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::rustlight_parser::parse_rust_source;

    fn cleanup_source(source: &str) -> (ComplexTypeCleanupAnalysis, RustModule, String) {
        let mut module = parse_rust_source(source, "test").expect("source should parse");
        let analysis = cleanup_complex_types(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        (analysis, module, printed)
    }

    #[test]
    fn shares_one_generic_alias_across_alpha_renamed_functions() {
        let source = r#"
            use std::rc::Rc;
            pub fn first<A>(f: Rc<dyn Fn(Rc<dyn Fn(A) -> (A, A)>, A) -> (A, A)>) -> () {}
            pub fn second<X>(f: Rc<dyn Fn(Rc<dyn Fn(X) -> (X, X)>, X) -> (X, X)>) -> () {}
        "#;
        let (analysis, _, printed) = cleanup_source(source);

        assert_eq!(analysis.aliases_created, 1);
        assert_eq!(analysis.rewritten_types, 2);
        assert!(printed.contains("pub type I2rComplexTypeH"));
        assert!(printed.contains(
            "<I2rT0> = Rc<dyn Fn(Rc<dyn Fn(I2rT0) -> (I2rT0, I2rT0)>, I2rT0) -> (I2rT0, I2rT0)>"
        ));

        let alias_name = printed
            .lines()
            .find_map(|line| line.trim().strip_prefix("pub type "))
            .and_then(|line| line.split('<').next())
            .expect("generated alias name");
        assert!(printed.contains(&format!("f: {alias_name}<A>")));
        assert!(printed.contains(&format!("f: {alias_name}<X>")));
    }

    #[test]
    fn rewrites_casts_but_keeps_reference_outside_alias() {
        let source = r#"
            use std::rc::Rc;
            pub fn borrow(f: &Rc<dyn Fn(Rc<dyn Fn(i32) -> (i32, i32)>, i32) -> (i32, i32)>) -> () {
                let _g = (Rc::new(move |g: Rc<dyn Fn(i32) -> (i32, i32)>, x: i32| -> (i32, i32) {
                    g(x)
                })) as Rc<dyn Fn(Rc<dyn Fn(i32) -> (i32, i32)>, i32) -> (i32, i32)>;
            }
        "#;
        let (analysis, _, printed) = cleanup_source(source);

        assert_eq!(analysis.aliases_created, 1);
        assert_eq!(analysis.rewritten_types, 2);
        let alias_name = printed
            .lines()
            .find_map(|line| line.trim().strip_prefix("pub type "))
            .and_then(|line| line.split_whitespace().next())
            .expect("generated alias name");
        assert!(printed.contains(&format!("f: &{alias_name}")));
        assert!(printed.contains(&format!("as {alias_name}")));
        assert!(!printed.contains("type I2rComplexTypeH") || !printed.contains("= &Rc<"));
    }

    #[test]
    fn leaves_impl_trait_types_unaliased() {
        let source = "pub fn make() -> impl Fn(i32) -> i32 { |x| x }";
        let (analysis, _, printed) = cleanup_source(source);

        assert_eq!(analysis.aliases_created, 0);
        assert!(printed.contains("-> impl Fn(i32) -> i32"));
    }

    #[test]
    fn leaves_types_below_clippys_default_threshold_unaliased() {
        let source = r#"
            use std::rc::Rc;
            pub fn apply(f: Rc<dyn Fn(i32) -> i32>) -> () {}
        "#;
        let (analysis, _, _) = cleanup_source(source);

        assert_eq!(analysis.aliases_created, 0);
        assert_eq!(analysis.rewritten_types, 0);
    }

    #[test]
    fn second_run_is_idempotent() {
        let source = r#"
            use std::rc::Rc;
            pub fn apply(f: Rc<dyn Fn(Rc<dyn Fn(i32) -> (i32, i32)>, i32) -> (i32, i32)>) -> () {}
        "#;
        let (_, mut module, first) = cleanup_source(source);
        let second_analysis = cleanup_complex_types(&mut module);
        let mut generator = RustCodeGenerator::new();
        let second = generator.generate_module_code(&module);

        assert_eq!(second_analysis.aliases_created, 0);
        assert_eq!(second_analysis.rewritten_types, 0);
        assert_eq!(first, second);
    }
}
