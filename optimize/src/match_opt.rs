use std::collections::{HashMap, HashSet};

use rustlightast::*;

/// Result of the match-cleanup pass.
#[derive(Debug, Clone, Default)]
pub struct MatchOptAnalysis {
    /// Removed trailing `_ => panic!("non-exhaustive match")` arms.
    pub removed_panic_arms: usize,
    /// Removed wildcard discard statements such as `let _ = expr;`.
    pub removed_wildcard_lets: usize,
    /// Removed identity shadowing statements such as `let x = x;`.
    pub removed_identity_lets: usize,
}

type TypeEnv = HashMap<String, Type>;

#[derive(Debug, Clone)]
struct EnumInfo {
    variants: Vec<VariantInfo>,
}

#[derive(Debug, Clone)]
struct VariantInfo {
    name: String,
    fields: Vec<Type>,
}

#[derive(Debug, Clone)]
enum CoverageCase {
    Any,
    Bool(bool),
    Variant(String),
}

/// Clean match artifacts left by the conservative stage-1 printer and earlier
/// ownership passes.
pub fn optimize_match(module: &mut RustModule) -> MatchOptAnalysis {
    let mut analysis = MatchOptAnalysis::default();
    optimize_module(module, &mut analysis);
    analysis
}

fn optimize_module(module: &mut RustModule, analysis: &mut MatchOptAnalysis) {
    let enum_defs = collect_enum_defs(&module.items);

    for item in &mut module.items {
        optimize_item(item, &enum_defs, analysis);
    }
}

fn optimize_item(
    item: &mut Item,
    enum_defs: &HashMap<String, EnumInfo>,
    analysis: &mut MatchOptAnalysis,
) {
    match item {
        Item::Function(function) => optimize_function(function, enum_defs, analysis),
        Item::Impl(impl_block) => {
            for impl_item in &mut impl_block.items {
                match impl_item {
                    ImplItem::Method(method) => optimize_function(method, enum_defs, analysis),
                    ImplItem::AssocConst(_, _, expr) => {
                        optimize_expr(expr, &mut TypeEnv::new(), enum_defs, analysis);
                    }
                    ImplItem::AssocType(_, _) => {}
                }
            }
        }
        Item::Const(const_def) => {
            optimize_expr(
                &mut const_def.value,
                &mut TypeEnv::new(),
                enum_defs,
                analysis,
            );
        }
        Item::LazyStatic(lazy_static) => {
            optimize_block(
                &mut lazy_static.init,
                &mut TypeEnv::new(),
                enum_defs,
                analysis,
            );
        }
        Item::Mod(inner) => optimize_module(inner, analysis),
        _ => {}
    }
}

fn optimize_function(
    function: &mut FunctionDef,
    enum_defs: &HashMap<String, EnumInfo>,
    analysis: &mut MatchOptAnalysis,
) {
    let mut env = function_type_env(function);
    optimize_block(&mut function.body, &mut env, enum_defs, analysis);
}

fn optimize_block(
    block: &mut Block,
    env: &mut TypeEnv,
    enum_defs: &HashMap<String, EnumInfo>,
    analysis: &mut MatchOptAnalysis,
) {
    let mut new_stmts = Vec::with_capacity(block.stmts.len());

    for stmt in std::mem::take(&mut block.stmts) {
        match stmt {
            Statement::Let(mut let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    optimize_expr(init, env, enum_defs, analysis);
                }

                if let_stmt.name.trim() == "_" {
                    analysis.removed_wildcard_lets += 1;
                    continue;
                }

                if is_identity_let(&let_stmt) {
                    analysis.removed_identity_lets += 1;
                    continue;
                }

                if let Some(ty) = let_stmt.ty.clone().or_else(|| {
                    let_stmt
                        .init
                        .as_ref()
                        .and_then(|init| infer_type(init, env))
                }) {
                    bind_pattern_env(&let_stmt.name, &ty, env, enum_defs);
                }

                new_stmts.push(Statement::Let(let_stmt));
            }
            Statement::Expr(mut expr) => {
                optimize_expr(&mut expr, env, enum_defs, analysis);
                new_stmts.push(Statement::Expr(expr));
            }
            Statement::Item(mut item) => {
                optimize_item(&mut item, enum_defs, analysis);
                new_stmts.push(Statement::Item(item));
            }
            other => new_stmts.push(other),
        }
    }

    block.stmts = new_stmts;

    if let Some(tail) = &mut block.expr {
        optimize_expr(tail, env, enum_defs, analysis);
    }
}

fn optimize_expr(
    expr: &mut Expr,
    env: &mut TypeEnv,
    enum_defs: &HashMap<String, EnumInfo>,
    analysis: &mut MatchOptAnalysis,
) {
    match expr {
        Expr::Call(callee, args) => {
            optimize_expr(callee, env, enum_defs, analysis);
            for arg in args {
                optimize_expr(arg, env, enum_defs, analysis);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            optimize_expr(receiver, env, enum_defs, analysis);
            for arg in args {
                optimize_expr(arg, env, enum_defs, analysis);
            }
        }
        Expr::Tuple(items) => {
            for item in items {
                optimize_expr(item, env, enum_defs, analysis);
            }
        }
        Expr::Block(block) => {
            let mut block_env = env.clone();
            optimize_block(block, &mut block_env, enum_defs, analysis);
        }
        Expr::Loop(block) | Expr::Unsafe(block) => {
            let mut block_env = env.clone();
            optimize_block(block, &mut block_env, enum_defs, analysis);
        }
        Expr::Closure(_, body, _) | Expr::Await(body) | Expr::Parenthesized(body) => {
            optimize_expr(body, env, enum_defs, analysis);
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            optimize_expr(condition, env, enum_defs, analysis);
            let mut then_env = env.clone();
            optimize_block(then_branch, &mut then_env, enum_defs, analysis);
            if let Some(else_branch) = else_branch {
                let mut else_env = env.clone();
                optimize_block(else_branch, &mut else_env, enum_defs, analysis);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            optimize_expr(value, env, enum_defs, analysis);
            let mut then_env = env.clone();
            optimize_block(then_branch, &mut then_env, enum_defs, analysis);
            if let Some(else_branch) = else_branch {
                let mut else_env = env.clone();
                optimize_block(else_branch, &mut else_env, enum_defs, analysis);
            }
        }
        Expr::Match {
            expr: scrutinee,
            arms,
        } => {
            optimize_expr(scrutinee, env, enum_defs, analysis);
            let scrutinee_ty = infer_type(scrutinee, env);

            for arm in arms.iter_mut() {
                if let Some(guard) = &mut arm.guard {
                    optimize_expr(guard, env, enum_defs, analysis);
                }

                let mut arm_env = env.clone();
                if let Some(ty) = scrutinee_ty.as_ref() {
                    bind_pattern_env(&arm.pattern, strip_ref_type(ty), &mut arm_env, enum_defs);
                }
                optimize_block(&mut arm.body, &mut arm_env, enum_defs, analysis);
            }

            if can_remove_trailing_panic_arm(scrutinee, arms, env, enum_defs) {
                arms.pop();
                analysis.removed_panic_arms += 1;
            }
        }
        Expr::Reference(inner, _, _)
        | Expr::UnaryOp(_, inner)
        | Expr::Index(inner, _)
        | Expr::Assign(inner, _) => {
            optimize_expr(inner, env, enum_defs, analysis);
            match expr {
                Expr::Index(_, index) | Expr::Assign(_, index) => {
                    optimize_expr(index, env, enum_defs, analysis);
                }
                _ => {}
            }
        }
        Expr::BinaryOp(left, _, right) => {
            optimize_expr(left, env, enum_defs, analysis);
            optimize_expr(right, env, enum_defs, analysis);
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    optimize_expr(closure, env, enum_defs, analysis);
                }
            }
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }
}

fn can_remove_trailing_panic_arm(
    scrutinee: &Expr,
    arms: &[MatchArm],
    env: &TypeEnv,
    enum_defs: &HashMap<String, EnumInfo>,
) -> bool {
    let Some((panic_arm, covered_arms)) = arms.split_last() else {
        return false;
    };
    if !is_nonexhaustive_panic_arm(panic_arm) {
        return false;
    }

    if covered_arms
        .iter()
        .any(|arm| arm.guard.is_none() && is_irrefutable_pattern(&arm.pattern))
    {
        return true;
    }

    let Some(scrutinee_ty) = infer_type(scrutinee, env) else {
        return false;
    };
    patterns_cover_type(covered_arms, strip_ref_type(&scrutinee_ty), enum_defs)
}

fn patterns_cover_type(
    arms: &[MatchArm],
    ty: &Type,
    enum_defs: &HashMap<String, EnumInfo>,
) -> bool {
    let ty = strip_ref_type(ty);
    if arms
        .iter()
        .any(|arm| arm.guard.is_none() && is_irrefutable_pattern(&arm.pattern))
    {
        return true;
    }

    if is_bool_type(ty) {
        let mut values = HashSet::new();
        for arm in arms.iter().filter(|arm| arm.guard.is_none()) {
            match arm.pattern.trim() {
                "true" => {
                    values.insert(true);
                }
                "false" => {
                    values.insert(false);
                }
                _ => {}
            }
        }
        return values.len() == 2;
    }

    if let Type::Tuple(types) = ty {
        return tuple_patterns_cover_type(arms, types, enum_defs);
    }

    let Some(enum_name) = local_type_name(ty) else {
        return false;
    };
    let Some(enum_info) = enum_defs.get(enum_name) else {
        return false;
    };

    let mut covered = HashSet::new();
    for arm in arms.iter().filter(|arm| arm.guard.is_none()) {
        if let Some(variant) = covered_variant(&arm.pattern, enum_name, enum_info) {
            covered.insert(variant);
        }
    }

    enum_info
        .variants
        .iter()
        .all(|variant| covered.contains(variant.name.as_str()))
}

fn tuple_patterns_cover_type(
    arms: &[MatchArm],
    types: &[Type],
    enum_defs: &HashMap<String, EnumInfo>,
) -> bool {
    let Some(rows) = tuple_pattern_rows(arms, types.len()) else {
        return false;
    };
    let Some(cases) = tuple_coverage_cases(types, enum_defs) else {
        return false;
    };
    let mut combinations = Vec::new();
    build_case_combinations(&cases, 0, &mut Vec::new(), &mut combinations);

    combinations.iter().all(|combination| {
        rows.iter()
            .any(|row| tuple_row_matches_cases(row, types, combination, enum_defs))
    })
}

fn tuple_pattern_rows(arms: &[MatchArm], arity: usize) -> Option<Vec<Vec<String>>> {
    arms.iter()
        .filter(|arm| arm.guard.is_none())
        .map(|arm| tuple_pattern_parts(&arm.pattern, arity))
        .collect()
}

fn tuple_pattern_parts(pattern: &str, arity: usize) -> Option<Vec<String>> {
    let pattern = strip_pattern_modifiers(pattern.trim());
    if is_irrefutable_pattern(pattern) {
        return Some(vec!["_".to_string(); arity]);
    }

    let inner = outer_parens_inner(pattern)?;
    let parts = split_top_level_commas(inner);
    if parts.len() == arity {
        Some(parts)
    } else {
        None
    }
}

fn tuple_coverage_cases(
    types: &[Type],
    enum_defs: &HashMap<String, EnumInfo>,
) -> Option<Vec<Vec<CoverageCase>>> {
    let mut product_size = 1usize;
    let mut cases = Vec::new();

    for ty in types {
        let ty_cases = coverage_cases_for_type(ty, enum_defs)?;
        product_size = product_size.checked_mul(ty_cases.len())?;
        if product_size > 1024 {
            return None;
        }
        cases.push(ty_cases);
    }

    Some(cases)
}

fn coverage_cases_for_type(
    ty: &Type,
    enum_defs: &HashMap<String, EnumInfo>,
) -> Option<Vec<CoverageCase>> {
    let ty = strip_ref_type(ty);
    if is_bool_type(ty) {
        return Some(vec![CoverageCase::Bool(false), CoverageCase::Bool(true)]);
    }

    if let Some(enum_name) = local_type_name(ty) {
        if let Some(enum_info) = enum_defs.get(enum_name) {
            return Some(
                enum_info
                    .variants
                    .iter()
                    .map(|variant| CoverageCase::Variant(variant.name.clone()))
                    .collect(),
            );
        }
    }

    Some(vec![CoverageCase::Any])
}

fn build_case_combinations(
    cases: &[Vec<CoverageCase>],
    idx: usize,
    current: &mut Vec<CoverageCase>,
    out: &mut Vec<Vec<CoverageCase>>,
) {
    if idx == cases.len() {
        out.push(current.clone());
        return;
    }

    for case in &cases[idx] {
        current.push(case.clone());
        build_case_combinations(cases, idx + 1, current, out);
        current.pop();
    }
}

fn tuple_row_matches_cases(
    row: &[String],
    types: &[Type],
    cases: &[CoverageCase],
    enum_defs: &HashMap<String, EnumInfo>,
) -> bool {
    row.iter()
        .zip(types.iter())
        .zip(cases.iter())
        .all(|((pattern, ty), case)| pattern_matches_case(pattern, ty, case, enum_defs))
}

fn pattern_matches_case(
    pattern: &str,
    ty: &Type,
    case: &CoverageCase,
    enum_defs: &HashMap<String, EnumInfo>,
) -> bool {
    let pattern = strip_pattern_modifiers(pattern.trim());
    if is_irrefutable_pattern(pattern) {
        return true;
    }

    match case {
        CoverageCase::Any => false,
        CoverageCase::Bool(value) => match pattern {
            "true" => *value,
            "false" => !*value,
            _ => false,
        },
        CoverageCase::Variant(expected) => {
            let Some(enum_name) = local_type_name(ty) else {
                return false;
            };
            let Some(enum_info) = enum_defs.get(enum_name) else {
                return false;
            };
            covered_variant(pattern, enum_name, enum_info)
                .is_some_and(|variant| variant == expected.as_str())
        }
    }
}

fn covered_variant<'a>(pattern: &str, enum_name: &str, enum_info: &'a EnumInfo) -> Option<&'a str> {
    let pattern = strip_pattern_modifiers(pattern.trim());
    let (constructor, args) = split_constructor_pattern(pattern)?;
    let (owner, variant_name) = split_constructor_path(constructor);

    if owner.is_some_and(|owner| owner != enum_name) {
        return None;
    }

    let variant = enum_info
        .variants
        .iter()
        .find(|variant| variant.name == variant_name)?;

    if variant.fields.len() != args.len() {
        return None;
    }
    if args
        .iter()
        .zip(variant.fields.iter())
        .all(|(arg, ty)| is_irrefutable_for_type(arg, ty))
    {
        Some(variant.name.as_str())
    } else {
        None
    }
}

fn is_nonexhaustive_panic_arm(arm: &MatchArm) -> bool {
    arm.pattern.trim() == "_"
        && arm.guard.is_none()
        && arm.body.stmts.is_empty()
        && matches!(
            arm.body.expr.as_deref(),
            Some(Expr::Macro(source)) if compact_tokens(source) == "panic!(\"non-exhaustivematch\")"
        )
}

fn is_identity_let(let_stmt: &LetStmt) -> bool {
    !let_stmt.ifmut
        && let_stmt.ty.is_none()
        && is_binding_ident(&let_stmt.name)
        && matches!(
            let_stmt.init.as_ref().map(strip_parens_expr),
            Some(Expr::Ident(name)) if name == &let_stmt.name
        )
}

fn strip_parens_expr(expr: &Expr) -> &Expr {
    match expr {
        Expr::Parenthesized(inner) => strip_parens_expr(inner),
        _ => expr,
    }
}

fn collect_enum_defs(items: &[Item]) -> HashMap<String, EnumInfo> {
    let mut enum_defs = HashMap::new();
    for item in items {
        if let Item::Enum(enum_def) = item {
            enum_defs.insert(
                enum_def.name.clone(),
                EnumInfo {
                    variants: enum_def
                        .variants
                        .iter()
                        .map(|variant| VariantInfo {
                            name: variant.name.clone(),
                            fields: variant.data.clone().unwrap_or_default(),
                        })
                        .collect(),
                },
            );
        }
    }
    enum_defs
}

fn function_type_env(function: &FunctionDef) -> TypeEnv {
    function
        .params
        .iter()
        .filter(|param| !param.name.is_empty())
        .map(|param| (param.name.clone(), param.ty.clone()))
        .collect()
}

fn bind_pattern_env(
    pattern: &str,
    ty: &Type,
    env: &mut TypeEnv,
    enum_defs: &HashMap<String, EnumInfo>,
) {
    let pattern = strip_pattern_modifiers(pattern.trim());
    if pattern.is_empty() || pattern == "_" || pattern == ".." {
        return;
    }

    if let Some(inner) = outer_parens_inner(pattern) {
        let parts = split_top_level_commas(inner);
        if parts.len() > 1 {
            if let Type::Tuple(types) = strip_ref_type(ty) {
                for (part, ty) in parts.iter().zip(types.iter()) {
                    bind_pattern_env(part, ty, env, enum_defs);
                }
            }
            return;
        }
    }

    if let Some((constructor, args)) = split_constructor_pattern(pattern) {
        if let Some(field_types) = pattern_field_types(constructor, strip_ref_type(ty), enum_defs) {
            for (arg, field_ty) in args.iter().zip(field_types.iter()) {
                bind_pattern_env(arg, field_ty, env, enum_defs);
            }
        }
        return;
    }

    if is_binding_ident(pattern) {
        env.insert(pattern.to_string(), strip_ref_type(ty).clone());
    }
}

fn pattern_field_types<'a>(
    constructor: &str,
    ty: &'a Type,
    enum_defs: &'a HashMap<String, EnumInfo>,
) -> Option<&'a [Type]> {
    let enum_name = local_type_name(ty)?;
    let enum_info = enum_defs.get(enum_name)?;
    let (owner, variant_name) = split_constructor_path(constructor);
    if owner.is_some_and(|owner| owner != enum_name) {
        return None;
    }
    enum_info
        .variants
        .iter()
        .find(|variant| variant.name == variant_name)
        .map(|variant| variant.fields.as_slice())
}

fn infer_type(expr: &Expr, env: &TypeEnv) -> Option<Type> {
    match expr {
        Expr::Ident(name) => env.get(name).cloned(),
        Expr::Reference(inner, true, is_mut) => {
            infer_type(inner, env).map(|ty| Type::Reference(Box::new(ty), true, *is_mut))
        }
        Expr::Parenthesized(inner) => infer_type(inner, env),
        Expr::Tuple(items) => items
            .iter()
            .map(|item| infer_type(item, env))
            .collect::<Option<Vec<_>>>()
            .map(Type::Tuple),
        Expr::MethodCall(receiver, method, args) if method == "as_ref" && args.is_empty() => {
            infer_type(receiver, env).and_then(|ty| match strip_ref_type(&ty) {
                Type::Generic(name, params) if name == "Box" && params.len() == 1 => {
                    Some(Type::Reference(Box::new(params[0].clone()), true, false))
                }
                inner => Some(Type::Reference(Box::new(inner.clone()), true, false)),
            })
        }
        Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
            infer_type(receiver, env).map(|ty| strip_ref_type(&ty).clone())
        }
        Expr::UnaryOp(op, inner) if op == "*" => infer_type(inner, env).and_then(|ty| match ty {
            Type::Generic(name, params) if name == "Box" && params.len() == 1 => {
                params.into_iter().next()
            }
            Type::Reference(inner, true, _) => Some(*inner),
            _ => None,
        }),
        _ => None,
    }
}

fn is_irrefutable_for_type(pattern: &str, ty: &Type) -> bool {
    let pattern = strip_pattern_modifiers(pattern.trim());
    if is_irrefutable_pattern(pattern) {
        return true;
    }

    if let Some(inner) = outer_parens_inner(pattern) {
        let parts = split_top_level_commas(inner);
        if parts.len() > 1 {
            if let Type::Tuple(types) = strip_ref_type(ty) {
                return parts.len() == types.len()
                    && parts
                        .iter()
                        .zip(types.iter())
                        .all(|(part, ty)| is_irrefutable_for_type(part, ty));
            }
        }
    }

    false
}

fn is_irrefutable_pattern(pattern: &str) -> bool {
    let pattern = strip_pattern_modifiers(pattern.trim());
    if pattern == "_" || pattern == ".." {
        return true;
    }

    if let Some(inner) = outer_parens_inner(pattern) {
        let parts = split_top_level_commas(inner);
        if parts.len() > 1 {
            return parts.iter().all(|part| is_irrefutable_pattern(part));
        }
    }

    is_binding_ident(pattern)
}

fn is_binding_ident(pattern: &str) -> bool {
    let mut chars = pattern.chars();
    let Some(first) = chars.next() else {
        return false;
    };

    (first == '_' || first.is_ascii_lowercase())
        && chars.all(|c| c == '_' || c.is_ascii_alphanumeric())
        && !matches!(pattern, "_" | "true" | "false" | "Some" | "None")
}

fn strip_pattern_modifiers(mut pattern: &str) -> &str {
    loop {
        let trimmed = pattern.trim();
        if let Some(rest) = strip_prefix_word(trimmed, "box") {
            pattern = rest;
        } else if let Some(rest) = strip_prefix_word(trimmed, "ref") {
            pattern = rest;
        } else if let Some(rest) = strip_prefix_word(trimmed, "mut") {
            pattern = rest;
        } else {
            return trimmed;
        }
    }
}

fn split_constructor_pattern(pattern: &str) -> Option<(&str, Vec<String>)> {
    let pattern = pattern.trim();
    if pattern.is_empty() || pattern == "_" || pattern == ".." {
        return None;
    }

    if let Some(idx) = first_top_level_paren(pattern) {
        let constructor = pattern[..idx].trim();
        let inner = matching_paren_inner(&pattern[idx..])?;
        if constructor.is_empty() {
            return None;
        }
        return Some((constructor, split_top_level_commas(inner)));
    }

    if pattern.contains("::") || starts_with_variant_case(pattern) {
        Some((pattern, Vec::new()))
    } else {
        None
    }
}

fn split_constructor_path(constructor: &str) -> (Option<&str>, &str) {
    match constructor.rsplit_once("::") {
        Some((owner, variant)) => (owner.rsplit("::").next(), variant),
        None => (None, constructor),
    }
}

fn outer_parens_inner(pattern: &str) -> Option<&str> {
    let pattern = pattern.trim();
    if !(pattern.starts_with('(') && pattern.ends_with(')')) {
        return None;
    }

    let mut depth = 0;
    for (idx, ch) in pattern.char_indices() {
        match ch {
            '(' => depth += 1,
            ')' => {
                depth -= 1;
                if depth == 0 && idx != pattern.len() - 1 {
                    return None;
                }
            }
            _ => {}
        }
    }

    (depth == 0).then_some(&pattern[1..pattern.len() - 1])
}

fn split_top_level_commas(input: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut start = 0;
    let mut depth = 0;

    for (idx, ch) in input.char_indices() {
        match ch {
            '(' | '[' | '{' => depth += 1,
            ')' | ']' | '}' => depth -= 1,
            ',' if depth == 0 => {
                parts.push(input[start..idx].trim().to_string());
                start = idx + ch.len_utf8();
            }
            _ => {}
        }
    }

    if start <= input.len() {
        let tail = input[start..].trim();
        if !tail.is_empty() {
            parts.push(tail.to_string());
        }
    }

    parts
}

fn first_top_level_paren(input: &str) -> Option<usize> {
    let mut angle_depth = 0;
    for (idx, ch) in input.char_indices() {
        match ch {
            '<' => angle_depth += 1,
            '>' => angle_depth -= 1,
            '(' if angle_depth == 0 => return Some(idx),
            _ => {}
        }
    }
    None
}

fn matching_paren_inner(input: &str) -> Option<&str> {
    let input = input.trim();
    if !(input.starts_with('(') && input.ends_with(')')) {
        return None;
    }
    outer_parens_inner(input)
}

fn strip_prefix_word<'a>(input: &'a str, word: &str) -> Option<&'a str> {
    input
        .strip_prefix(word)
        .filter(|rest| rest.starts_with(char::is_whitespace))
        .map(str::trim_start)
}

fn starts_with_variant_case(pattern: &str) -> bool {
    pattern
        .chars()
        .next()
        .is_some_and(|ch| ch.is_ascii_uppercase())
}

fn strip_ref_type(ty: &Type) -> &Type {
    match ty {
        Type::Reference(inner, true, _) => strip_ref_type(inner),
        _ => ty,
    }
}

fn local_type_name(ty: &Type) -> Option<&str> {
    match strip_ref_type(ty) {
        Type::Named(name) => Some(name.as_str()),
        Type::Path(path) => path.last().map(String::as_str),
        Type::Generic(name, _) => Some(name.as_str()),
        _ => None,
    }
}

fn is_bool_type(ty: &Type) -> bool {
    matches!(strip_ref_type(ty), Type::Named(name) if name == "bool")
}

fn compact_tokens(input: &str) -> String {
    input.chars().filter(|ch| !ch.is_whitespace()).collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parse_rust_source;

    fn optimize_and_print(source: &str) -> (MatchOptAnalysis, String) {
        let mut module = parse_rust_source(source, "Test").expect("parse source");
        let analysis = optimize_match(&mut module);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        (analysis, printed)
    }

    #[test]
    fn removes_exhaustive_enum_fallback_and_wildcard_lets() {
        let source = r#"
#[derive(Clone)]
pub enum Cotree {
    CoLeaf,
    CoNode(Box<Cotree>, Box<Cotree>),
}

pub fn is_leaf(x0: &Cotree) -> bool {
    match x0 {
        Cotree::CoLeaf => { true },
        Cotree::CoNode(p0, p0a) => {
            let _ = p0.as_ref().clone();
            let _ = p0a.as_ref().clone();
            false
        },
        _ => { panic!("non-exhaustive match") },
    }
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.removed_wildcard_lets, 2);
        assert_eq!(analysis.removed_panic_arms, 1);
        assert!(!printed.contains("let _ ="));
        assert!(!printed.contains(r#"panic!("non-exhaustive match")"#));
    }

    #[test]
    fn removes_identity_lets() {
        let source = r#"
pub fn keep_value(x: i32) -> i32 {
    let x = x;
    let y = x;
    y
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.removed_identity_lets, 1);
        assert!(!printed.contains("let x = x;"));
        assert!(printed.contains("let y = x;"));
    }

    #[test]
    fn keeps_partial_enum_fallback() {
        let source = r#"
#[derive(Clone)]
pub enum Rlist<A> {
    RNil,
    RCons(A, Box<Rlist<A>>),
}

pub fn head<A>(x0: Rlist<A>) -> A
where
    A: Clone + 'static,
{
    match x0 {
        Rlist::RCons(x, xs) => { x.clone() },
        _ => { panic!("non-exhaustive match") },
    }
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.removed_panic_arms, 0);
        assert!(printed.contains(r#"panic!("non-exhaustive match")"#));
    }

    #[test]
    fn removes_fallback_after_irrefutable_arm() {
        let source = r#"
pub fn id_bool(x: bool) -> bool {
    match x {
        y => { y },
        _ => { panic!("non-exhaustive match") },
    }
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.removed_panic_arms, 1);
        assert!(!printed.contains(r#"panic!("non-exhaustive match")"#));
    }

    #[test]
    fn removes_exhaustive_tuple_enum_fallback() {
        let source = r#"
#[derive(Clone)]
pub enum ValueSlot<A> {
    Empty,
    Value(A),
}

pub fn value_or<A>(d: A, x: ValueSlot<A>) -> A
where
    A: Clone + 'static,
{
    match (d, x) {
        (d, ValueSlot::Empty) => { d.clone() },
        (_, ValueSlot::Value(x)) => { x.clone() },
        _ => { panic!("non-exhaustive match") },
    }
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.removed_panic_arms, 1);
        assert!(!printed.contains(r#"panic!("non-exhaustive match")"#));
    }

    #[test]
    fn keeps_partial_tuple_enum_fallback() {
        let source = r#"
#[derive(Clone)]
pub enum ValueSlot<A> {
    Empty,
    Value(A),
}

pub fn only_empty<A>(d: A, x: ValueSlot<A>) -> A
where
    A: Clone + 'static,
{
    match (d, x) {
        (d, ValueSlot::Empty) => { d.clone() },
        _ => { panic!("non-exhaustive match") },
    }
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.removed_panic_arms, 0);
        assert!(printed.contains(r#"panic!("non-exhaustive match")"#));
    }
}
