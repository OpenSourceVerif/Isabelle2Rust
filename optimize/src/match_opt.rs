use std::collections::{HashMap, HashSet};

use rustlightast::*;

/// Result of the match-cleanup pass.
#[derive(Debug, Clone, Default)]
pub struct MatchOptAnalysis {
    /// Removed trailing `_ => panic!("non-exhaustive match")` arms.
    pub removed_panic_arms: usize,
    /// Rewrote single-arm irrefutable matches to scoped `let` bindings.
    pub collapsed_single_arm_matches: usize,
}

type TypeEnv = HashMap<String, Type>;

#[derive(Debug, Clone, Default)]
pub struct MatchTypeContext {
    function_returns: HashMap<Vec<String>, Type>,
    enum_defs: HashMap<Vec<String>, EnumInfo>,
}

impl MatchTypeContext {
    pub fn insert_module(&mut self, module_path: Vec<String>, module: &RustModule) {
        self.collect_module(module_path, module);
    }

    fn collect_module(&mut self, module_path: Vec<String>, module: &RustModule) {
        for item in &module.items {
            match item {
                Item::Function(function) => {
                    let mut function_path = module_path.clone();
                    function_path.push(function.name.clone());
                    self.function_returns
                        .insert(function_path, function.return_type.clone());
                }
                Item::Enum(enum_def) => {
                    let mut enum_path = module_path.clone();
                    enum_path.push(enum_def.name.clone());
                    self.enum_defs.insert(
                        enum_path,
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
                Item::Mod(inner) => {
                    let mut inner_path = module_path.clone();
                    inner_path.push(inner.name.clone());
                    self.collect_module(inner_path, inner);
                }
                _ => {}
            }
        }
    }
}

struct MatchScope<'a> {
    context: &'a MatchTypeContext,
    module_path: Vec<String>,
    imports: HashMap<String, Vec<String>>,
}

impl MatchScope<'_> {
    fn resolve_name_path(&self, name: &str) -> Vec<String> {
        if let Some(path) = self.imports.get(name) {
            return path.clone();
        }

        let mut path = self.module_path.clone();
        path.push(name.to_string());
        path
    }

    fn resolve_segments(&self, segments: &[String]) -> Vec<String> {
        let Some((first, rest)) = segments.split_first() else {
            return Vec::new();
        };

        match first.as_str() {
            "crate" => segments.to_vec(),
            "self" => {
                let mut path = self.module_path.clone();
                path.extend(rest.iter().cloned());
                path
            }
            "super" => {
                let mut path = self.module_path.clone();
                let mut remaining = segments;
                while matches!(remaining.first().map(String::as_str), Some("super")) {
                    path.pop();
                    remaining = &remaining[1..];
                }
                path.extend(remaining.iter().cloned());
                path
            }
            _ => {
                if let Some(imported) = self.imports.get(first) {
                    let mut path = imported.clone();
                    path.extend(rest.iter().cloned());
                    path
                } else if segments.len() == 1 {
                    self.resolve_name_path(first)
                } else {
                    let mut path = vec!["crate".to_string()];
                    path.extend(segments.iter().cloned());
                    path
                }
            }
        }
    }

    fn resolve_type_path(&self, ty: &Type) -> Option<Vec<String>> {
        match strip_ref_type(ty) {
            Type::Named(name) => Some(self.resolve_name_path(name)),
            Type::Path(path) => Some(self.resolve_segments(path)),
            Type::Generic(name, _) => Some(self.resolve_name_path(name)),
            _ => None,
        }
    }

    fn enum_info_for_type(&self, ty: &Type) -> Option<&EnumInfo> {
        let path = self.resolve_type_path(ty)?;
        self.context.enum_defs.get(&path)
    }

    fn return_type_for_callee(&self, callee: &Expr, env: &TypeEnv) -> Option<Type> {
        let path = match callee {
            Expr::Ident(name) if env.contains_key(name) => return None,
            Expr::Ident(name) => self.resolve_name_path(name),
            Expr::Path(segments, PathType::Namespace) => self.resolve_segments(segments),
            Expr::Parenthesized(inner) => return self.return_type_for_callee(inner, env),
            _ => return None,
        };

        self.context.function_returns.get(&path).cloned()
    }
}

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
    let module_path = vec!["crate".to_string(), module.name.clone()];
    let mut context = MatchTypeContext::default();
    context.insert_module(module_path.clone(), module);
    optimize_match_with_context(module, &context, &module_path)
}

pub fn optimize_match_with_context(
    module: &mut RustModule,
    context: &MatchTypeContext,
    module_path: &[String],
) -> MatchOptAnalysis {
    let mut analysis = MatchOptAnalysis::default();
    optimize_module(module, context, module_path, &mut analysis);
    analysis
}

fn optimize_module(
    module: &mut RustModule,
    context: &MatchTypeContext,
    module_path: &[String],
    analysis: &mut MatchOptAnalysis,
) {
    let scope = MatchScope {
        context,
        module_path: module_path.to_vec(),
        imports: collect_imports(&module.items),
    };

    for item in &mut module.items {
        optimize_item(item, &scope, analysis);
    }
}

fn optimize_item(item: &mut Item, scope: &MatchScope, analysis: &mut MatchOptAnalysis) {
    match item {
        Item::Function(function) => optimize_function(function, scope, analysis),
        Item::Impl(impl_block) => {
            for impl_item in &mut impl_block.items {
                match impl_item {
                    ImplItem::Method(method) => optimize_function(method, scope, analysis),
                    ImplItem::AssocConst(_, _, expr) => {
                        optimize_expr(expr, &mut TypeEnv::new(), scope, analysis);
                    }
                    ImplItem::AssocType(_, _) => {}
                }
            }
        }
        Item::Const(const_def) => {
            optimize_expr(&mut const_def.value, &mut TypeEnv::new(), scope, analysis);
        }
        Item::LazyStatic(lazy_static) => {
            optimize_block(&mut lazy_static.init, &mut TypeEnv::new(), scope, analysis);
        }
        Item::Mod(inner) => {
            let mut inner_path = scope.module_path.clone();
            inner_path.push(inner.name.clone());
            optimize_module(inner, scope.context, &inner_path, analysis);
        }
        _ => {}
    }
}

fn optimize_function(
    function: &mut FunctionDef,
    scope: &MatchScope,
    analysis: &mut MatchOptAnalysis,
) {
    let mut env = function_type_env(function);
    optimize_block(&mut function.body, &mut env, scope, analysis);
}

fn optimize_block(
    block: &mut Block,
    env: &mut TypeEnv,
    scope: &MatchScope,
    analysis: &mut MatchOptAnalysis,
) {
    let mut new_stmts = Vec::with_capacity(block.stmts.len());

    for stmt in std::mem::take(&mut block.stmts) {
        match stmt {
            Statement::Let(mut let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    optimize_expr(init, env, scope, analysis);
                }

                if let Some(ty) = let_stmt.ty.clone().or_else(|| {
                    let_stmt
                        .init
                        .as_ref()
                        .and_then(|init| infer_type(init, env, scope))
                }) {
                    bind_pattern_env(&let_stmt.name, &ty, env, scope);
                }

                new_stmts.push(Statement::Let(let_stmt));
            }
            Statement::Expr(mut expr) => {
                optimize_expr(&mut expr, env, scope, analysis);
                new_stmts.push(Statement::Expr(expr));
            }
            Statement::Item(mut item) => {
                optimize_item(&mut item, scope, analysis);
                new_stmts.push(Statement::Item(item));
            }
            other => new_stmts.push(other),
        }
    }

    block.stmts = new_stmts;

    if let Some(tail) = &mut block.expr {
        optimize_expr(tail, env, scope, analysis);
    }
}

fn optimize_expr(
    expr: &mut Expr,
    env: &mut TypeEnv,
    scope: &MatchScope,
    analysis: &mut MatchOptAnalysis,
) {
    match expr {
        Expr::Call(callee, args) => {
            optimize_expr(callee, env, scope, analysis);
            for arg in args {
                optimize_expr(arg, env, scope, analysis);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            optimize_expr(receiver, env, scope, analysis);
            for arg in args {
                optimize_expr(arg, env, scope, analysis);
            }
        }
        Expr::Tuple(items) => {
            for item in items {
                optimize_expr(item, env, scope, analysis);
            }
        }
        Expr::Block(block) => {
            let mut block_env = env.clone();
            optimize_block(block, &mut block_env, scope, analysis);
        }
        Expr::Loop(block) | Expr::Unsafe(block) => {
            let mut block_env = env.clone();
            optimize_block(block, &mut block_env, scope, analysis);
        }
        Expr::Closure(_, body, _)
        | Expr::Await(body)
        | Expr::Parenthesized(body)
        | Expr::Cast(body, _) => {
            optimize_expr(body, env, scope, analysis);
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            optimize_expr(condition, env, scope, analysis);
            let mut then_env = env.clone();
            optimize_block(then_branch, &mut then_env, scope, analysis);
            if let Some(else_branch) = else_branch {
                let mut else_env = env.clone();
                optimize_block(else_branch, &mut else_env, scope, analysis);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            optimize_expr(value, env, scope, analysis);
            let mut then_env = env.clone();
            optimize_block(then_branch, &mut then_env, scope, analysis);
            if let Some(else_branch) = else_branch {
                let mut else_env = env.clone();
                optimize_block(else_branch, &mut else_env, scope, analysis);
            }
        }
        Expr::Match {
            expr: scrutinee,
            arms,
        } => {
            optimize_expr(scrutinee, env, scope, analysis);
            let scrutinee_ty = infer_type(scrutinee, env, scope);

            for arm in arms.iter_mut() {
                if let Some(guard) = &mut arm.guard {
                    optimize_expr(guard, env, scope, analysis);
                }

                let mut arm_env = env.clone();
                if let Some(ty) = scrutinee_ty.as_ref() {
                    bind_pattern_env(&arm.pattern, strip_ref_type(ty), &mut arm_env, scope);
                }
                optimize_block(&mut arm.body, &mut arm_env, scope, analysis);
            }

            if can_remove_trailing_fallback_arm(scrutinee, arms, env, scope) {
                if let Some(removed) = arms.pop() {
                    analysis.removed_panic_arms += count_nonexhaustive_panics_in_arm(&removed);
                }
            }

            let replacement = collapse_single_irrefutable_match(scrutinee, arms);
            if let Some(replacement) = replacement {
                *expr = replacement;
                analysis.collapsed_single_arm_matches += 1;
            }
        }
        Expr::Reference(inner, _, _)
        | Expr::UnaryOp(_, inner)
        | Expr::Index(inner, _)
        | Expr::Assign(inner, _) => {
            optimize_expr(inner, env, scope, analysis);
            match expr {
                Expr::Index(_, index) | Expr::Assign(_, index) => {
                    optimize_expr(index, env, scope, analysis);
                }
                _ => {}
            }
        }
        Expr::BinaryOp(left, _, right) => {
            optimize_expr(left, env, scope, analysis);
            optimize_expr(right, env, scope, analysis);
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    optimize_expr(closure, env, scope, analysis);
                }
            }
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }
}

fn can_remove_trailing_fallback_arm(
    scrutinee: &Expr,
    arms: &[MatchArm],
    env: &TypeEnv,
    scope: &MatchScope,
) -> bool {
    let Some((fallback_arm, covered_arms)) = arms.split_last() else {
        return false;
    };
    if fallback_arm.pattern.trim() != "_" || fallback_arm.guard.is_some() {
        return false;
    }

    if covered_arms
        .iter()
        .any(|arm| arm.guard.is_none() && is_irrefutable_pattern(&arm.pattern))
    {
        return true;
    }

    let Some(scrutinee_ty) = infer_type(scrutinee, env, scope) else {
        return false;
    };
    patterns_cover_type(covered_arms, strip_ref_type(&scrutinee_ty), scope)
}

fn collapse_single_irrefutable_match(scrutinee: &Expr, arms: &[MatchArm]) -> Option<Expr> {
    let [arm] = arms else {
        return None;
    };
    if arm.guard.is_some() || !is_irrefutable_pattern(&arm.pattern) {
        return None;
    }

    let mut stmts = Vec::with_capacity(arm.body.stmts.len() + 1);
    stmts.push(Statement::Let(LetStmt {
        ifmut: false,
        name: arm.pattern.trim().to_string(),
        ty: None,
        init: Some(scrutinee.clone()),
    }));
    stmts.extend(arm.body.stmts.iter().cloned());

    Some(Expr::Block(Block {
        stmts,
        expr: arm.body.expr.clone(),
    }))
}

fn patterns_cover_type(arms: &[MatchArm], ty: &Type, scope: &MatchScope) -> bool {
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
        return tuple_patterns_cover_type(arms, types, scope);
    }

    let Some(enum_info) = scope.enum_info_for_type(ty) else {
        return false;
    };

    let mut covered = HashSet::new();
    for arm in arms.iter().filter(|arm| arm.guard.is_none()) {
        if let Some(variant) = covered_variant(&arm.pattern, ty, scope) {
            covered.insert(variant);
        }
    }

    enum_info
        .variants
        .iter()
        .all(|variant| covered.contains(variant.name.as_str()))
}

fn tuple_patterns_cover_type(arms: &[MatchArm], types: &[Type], scope: &MatchScope) -> bool {
    let Some(rows) = tuple_pattern_rows(arms, types.len()) else {
        return false;
    };
    let Some(cases) = tuple_coverage_cases(types, scope) else {
        return false;
    };
    let mut combinations = Vec::new();
    build_case_combinations(&cases, 0, &mut Vec::new(), &mut combinations);

    combinations.iter().all(|combination| {
        rows.iter()
            .any(|row| tuple_row_matches_cases(row, types, combination, scope))
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

fn tuple_coverage_cases(types: &[Type], scope: &MatchScope) -> Option<Vec<Vec<CoverageCase>>> {
    let mut product_size = 1usize;
    let mut cases = Vec::new();

    for ty in types {
        let ty_cases = coverage_cases_for_type(ty, scope)?;
        product_size = product_size.checked_mul(ty_cases.len())?;
        if product_size > 1024 {
            return None;
        }
        cases.push(ty_cases);
    }

    Some(cases)
}

fn coverage_cases_for_type(ty: &Type, scope: &MatchScope) -> Option<Vec<CoverageCase>> {
    let ty = strip_ref_type(ty);
    if is_bool_type(ty) {
        return Some(vec![CoverageCase::Bool(false), CoverageCase::Bool(true)]);
    }

    if let Some(enum_info) = scope.enum_info_for_type(ty) {
        return Some(
            enum_info
                .variants
                .iter()
                .map(|variant| CoverageCase::Variant(variant.name.clone()))
                .collect(),
        );
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
    scope: &MatchScope,
) -> bool {
    row.iter()
        .zip(types.iter())
        .zip(cases.iter())
        .all(|((pattern, ty), case)| pattern_matches_case(pattern, ty, case, scope))
}

fn pattern_matches_case(pattern: &str, ty: &Type, case: &CoverageCase, scope: &MatchScope) -> bool {
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
            covered_variant(pattern, ty, scope).is_some_and(|variant| variant == expected.as_str())
        }
    }
}

fn covered_variant(pattern: &str, ty: &Type, scope: &MatchScope) -> Option<String> {
    let pattern = strip_pattern_modifiers(pattern.trim());
    let (constructor, args) = split_constructor_pattern(pattern)?;
    let (owner, variant_name) = split_constructor_path(constructor);
    let enum_path = scope.resolve_type_path(ty)?;

    if let Some(owner) = owner {
        if scope.resolve_segments(&owner) != enum_path {
            return None;
        }
    }

    let enum_info = scope.context.enum_defs.get(&enum_path)?;
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
        .all(|(arg, ty)| is_irrefutable_for_type(arg, ty, scope))
    {
        Some(variant.name.clone())
    } else {
        None
    }
}

fn count_nonexhaustive_panics_in_arm(arm: &MatchArm) -> usize {
    count_nonexhaustive_panics_in_block(&arm.body)
}

fn count_nonexhaustive_panics_in_block(block: &Block) -> usize {
    block
        .stmts
        .iter()
        .map(count_nonexhaustive_panics_in_stmt)
        .sum::<usize>()
        + block
            .expr
            .as_deref()
            .map(count_nonexhaustive_panics_in_expr)
            .unwrap_or(0)
}

fn count_nonexhaustive_panics_in_stmt(stmt: &Statement) -> usize {
    match stmt {
        Statement::Let(let_stmt) => let_stmt
            .init
            .as_ref()
            .map(count_nonexhaustive_panics_in_expr)
            .unwrap_or(0),
        Statement::Expr(expr) => count_nonexhaustive_panics_in_expr(expr),
        Statement::Item(item) => count_nonexhaustive_panics_in_item(item),
        Statement::Continue | Statement::Break | Statement::Comment(_) => 0,
    }
}

fn count_nonexhaustive_panics_in_item(item: &Item) -> usize {
    match item {
        Item::Function(function) => count_nonexhaustive_panics_in_block(&function.body),
        Item::Impl(impl_block) => impl_block
            .items
            .iter()
            .map(|item| match item {
                ImplItem::Method(method) => count_nonexhaustive_panics_in_block(&method.body),
                ImplItem::AssocConst(_, _, expr) => count_nonexhaustive_panics_in_expr(expr),
                ImplItem::AssocType(_, _) => 0,
            })
            .sum(),
        Item::Const(const_def) => count_nonexhaustive_panics_in_expr(&const_def.value),
        Item::LazyStatic(lazy_static) => count_nonexhaustive_panics_in_block(&lazy_static.init),
        Item::Mod(inner) => inner
            .items
            .iter()
            .map(count_nonexhaustive_panics_in_item)
            .sum(),
        _ => 0,
    }
}

fn count_nonexhaustive_panics_in_expr(expr: &Expr) -> usize {
    match expr {
        Expr::Macro(source) if compact_tokens(source) == "panic!(\"non-exhaustivematch\")" => 1,
        Expr::Call(callee, args) => {
            count_nonexhaustive_panics_in_expr(callee)
                + args
                    .iter()
                    .map(count_nonexhaustive_panics_in_expr)
                    .sum::<usize>()
        }
        Expr::MethodCall(receiver, _, args) => {
            count_nonexhaustive_panics_in_expr(receiver)
                + args
                    .iter()
                    .map(count_nonexhaustive_panics_in_expr)
                    .sum::<usize>()
        }
        Expr::Tuple(items) => items.iter().map(count_nonexhaustive_panics_in_expr).sum(),
        Expr::Block(block) => count_nonexhaustive_panics_in_block(block),
        Expr::Loop(block) | Expr::Unsafe(block) => count_nonexhaustive_panics_in_block(block),
        Expr::Closure(_, body, _)
        | Expr::Await(body)
        | Expr::Parenthesized(body)
        | Expr::Cast(body, _)
        | Expr::Reference(body, _, _)
        | Expr::UnaryOp(_, body) => count_nonexhaustive_panics_in_expr(body),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            count_nonexhaustive_panics_in_expr(condition)
                + count_nonexhaustive_panics_in_block(then_branch)
                + else_branch
                    .as_ref()
                    .map(count_nonexhaustive_panics_in_block)
                    .unwrap_or(0)
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            count_nonexhaustive_panics_in_expr(value)
                + count_nonexhaustive_panics_in_block(then_branch)
                + else_branch
                    .as_ref()
                    .map(count_nonexhaustive_panics_in_block)
                    .unwrap_or(0)
        }
        Expr::Match { expr, arms } => {
            count_nonexhaustive_panics_in_expr(expr)
                + arms
                    .iter()
                    .map(count_nonexhaustive_panics_in_arm)
                    .sum::<usize>()
        }
        Expr::Index(base, index) | Expr::Assign(base, index) | Expr::BinaryOp(base, _, index) => {
            count_nonexhaustive_panics_in_expr(base) + count_nonexhaustive_panics_in_expr(index)
        }
        Expr::BuilderChain(methods) => methods
            .iter()
            .map(|method| match method {
                BuilderMethod::Spawn { closure, .. } => count_nonexhaustive_panics_in_expr(closure),
                _ => 0,
            })
            .sum(),
        Expr::Ident(_) | Expr::Path(_, _) | Expr::Literal(_) | Expr::Macro(_) => 0,
    }
}

fn collect_imports(items: &[Item]) -> HashMap<String, Vec<String>> {
    let mut imports = HashMap::new();
    for item in items {
        if let Item::Use(use_stmt) = item {
            collect_import(&mut imports, use_stmt);
        }
    }
    imports
}

fn collect_import(imports: &mut HashMap<String, Vec<String>>, use_stmt: &UseStatement) {
    match &use_stmt.kind {
        UseKind::Simple => {
            if let Some((source, local)) = imported_leaf(use_stmt.path.last()) {
                let mut path = use_stmt.path.clone();
                if let Some(last) = path.last_mut() {
                    *last = source;
                }
                imports.insert(local, path);
            }
        }
        UseKind::Nested(items) => {
            for item in items {
                if let Some((source, local)) = imported_leaf(Some(item)) {
                    let mut path = use_stmt.path.clone();
                    path.push(source);
                    imports.insert(local, path);
                }
            }
        }
        UseKind::Glob => {}
    }
}

fn imported_leaf(leaf: Option<&String>) -> Option<(String, String)> {
    let leaf = leaf?.trim();
    if let Some((source, local)) = leaf.split_once(" as ") {
        Some((source.trim().to_string(), local.trim().to_string()))
    } else {
        Some((leaf.to_string(), leaf.to_string()))
    }
}

fn function_type_env(function: &FunctionDef) -> TypeEnv {
    function
        .params
        .iter()
        .filter(|param| !param.name.is_empty())
        .map(|param| (param.name.clone(), param.ty.clone()))
        .collect()
}

fn bind_pattern_env(pattern: &str, ty: &Type, env: &mut TypeEnv, scope: &MatchScope) {
    let pattern = strip_pattern_modifiers(pattern.trim());
    if pattern.is_empty() || pattern == "_" || pattern == ".." {
        return;
    }

    if let Some(inner) = outer_parens_inner(pattern) {
        let parts = split_top_level_commas(inner);
        if parts.len() > 1 {
            if let Type::Tuple(types) = strip_ref_type(ty) {
                for (part, ty) in parts.iter().zip(types.iter()) {
                    bind_pattern_env(part, ty, env, scope);
                }
            }
            return;
        }
    }

    if let Some((constructor, args)) = split_constructor_pattern(pattern) {
        if let Some(field_types) = pattern_field_types(constructor, strip_ref_type(ty), scope) {
            for (arg, field_ty) in args.iter().zip(field_types.iter()) {
                bind_pattern_env(arg, field_ty, env, scope);
            }
        }
        return;
    }

    if is_binding_ident(pattern) {
        env.insert(pattern.to_string(), strip_ref_type(ty).clone());
    }
}

fn pattern_field_types(constructor: &str, ty: &Type, scope: &MatchScope) -> Option<Vec<Type>> {
    let enum_path = scope.resolve_type_path(ty)?;
    let enum_info = scope.context.enum_defs.get(&enum_path)?;
    let (owner, variant_name) = split_constructor_path(constructor);
    if let Some(owner) = owner {
        if scope.resolve_segments(&owner) != enum_path {
            return None;
        }
    }
    enum_info
        .variants
        .iter()
        .find(|variant| variant.name == variant_name)
        .map(|variant| variant.fields.clone())
}

fn infer_type(expr: &Expr, env: &TypeEnv, scope: &MatchScope) -> Option<Type> {
    match expr {
        Expr::Ident(name) => env.get(name).cloned(),
        Expr::Reference(inner, true, is_mut) => {
            infer_type(inner, env, scope).map(|ty| Type::Reference(Box::new(ty), true, *is_mut))
        }
        Expr::Parenthesized(inner) => infer_type(inner, env, scope),
        Expr::Cast(_, ty) => Some(ty.clone()),
        Expr::Call(callee, _) => scope.return_type_for_callee(callee, env),
        Expr::Tuple(items) => items
            .iter()
            .map(|item| infer_type(item, env, scope))
            .collect::<Option<Vec<_>>>()
            .map(Type::Tuple),
        Expr::MethodCall(receiver, method, args) if method == "as_ref" && args.is_empty() => {
            infer_type(receiver, env, scope).and_then(|ty| match strip_ref_type(&ty) {
                Type::Generic(name, params) if name == "Box" && params.len() == 1 => {
                    Some(Type::Reference(Box::new(params[0].clone()), true, false))
                }
                inner => Some(Type::Reference(Box::new(inner.clone()), true, false)),
            })
        }
        Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
            infer_type(receiver, env, scope).map(|ty| strip_ref_type(&ty).clone())
        }
        Expr::UnaryOp(op, inner) if op == "*" => {
            infer_type(inner, env, scope).and_then(|ty| match ty {
                Type::Generic(name, params) if name == "Box" && params.len() == 1 => {
                    params.into_iter().next()
                }
                Type::Reference(inner, true, _) => Some(*inner),
                _ => None,
            })
        }
        _ => None,
    }
}

fn is_irrefutable_for_type(pattern: &str, ty: &Type, scope: &MatchScope) -> bool {
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
                        .all(|(part, ty)| is_irrefutable_for_type(part, ty, scope));
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

fn split_constructor_path(constructor: &str) -> (Option<Vec<String>>, &str) {
    match constructor.rsplit_once("::") {
        Some((owner, variant)) => (
            Some(owner.split("::").map(|part| part.to_string()).collect()),
            variant,
        ),
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

    fn optimize_with_modules(
        modules: Vec<(Vec<&str>, &str, &str)>,
        target_idx: usize,
    ) -> (MatchOptAnalysis, String) {
        let mut parsed = modules
            .into_iter()
            .map(|(path, name, source)| {
                (
                    path.into_iter().map(str::to_string).collect::<Vec<_>>(),
                    parse_rust_source(source, name).expect("parse source"),
                )
            })
            .collect::<Vec<_>>();

        let mut context = MatchTypeContext::default();
        for (path, module) in &parsed {
            context.insert_module(path.clone(), module);
        }

        let (path, module) = &mut parsed[target_idx];
        let analysis = optimize_match_with_context(module, &context, path);
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(module);
        (analysis, printed)
    }

    #[test]
    fn removes_exhaustive_enum_fallback() {
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
            false
        },
        _ => { panic!("non-exhaustive match") },
    }
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.removed_panic_arms, 1);
        assert!(!printed.contains(r#"panic!("non-exhaustive match")"#));
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
        assert_eq!(analysis.collapsed_single_arm_matches, 1);
        assert!(!printed.contains(r#"panic!("non-exhaustive match")"#));
        assert!(printed.contains("let y = x;"));
        assert!(!printed.contains("match x"));
    }

    #[test]
    fn removes_cross_module_bool_call_fallback() {
        let int_source = r#"
#[derive(Clone)]
pub enum Int {
    ZeroInt,
}

pub fn less_int(x0: Int, x1: Int) -> bool {
    true
}
"#;

        let basic_source = r#"
use crate::Int::Int;
use crate::Int::less_int;

pub fn max_case(a: Int, b: Int) -> Int {
    match less_int(b.clone(), a.clone()) {
        true => { a },
        false => { b },
        _ => { panic!("non-exhaustive match") },
    }
}
"#;

        let (analysis, printed) = optimize_with_modules(
            vec![
                (vec!["crate", "Int"], "Int", int_source),
                (
                    vec!["crate", "BasicDefinitions_Test"],
                    "BasicDefinitions_Test",
                    basic_source,
                ),
            ],
            1,
        );
        assert_eq!(analysis.removed_panic_arms, 1);
        assert!(!printed.contains(r#"panic!("non-exhaustive match")"#));
    }

    #[test]
    fn removes_imported_enum_fallback() {
        let arith_source = r#"
#[derive(Clone)]
pub enum Num {
    One,
    Bit0(Box<Num>),
    Bit1(Box<Num>),
}
"#;

        let int_source = r#"
use crate::Arith::Num;

pub fn is_num(x0: Num) -> bool {
    match x0 {
        Num::One => { true },
        Num::Bit0(_) => { true },
        Num::Bit1(_) => { true },
        _ => { panic!("non-exhaustive match") },
    }
}
"#;

        let (analysis, printed) = optimize_with_modules(
            vec![
                (vec!["crate", "Arith"], "Arith", arith_source),
                (vec!["crate", "Int"], "Int", int_source),
            ],
            1,
        );
        assert_eq!(analysis.removed_panic_arms, 1);
        assert!(!printed.contains(r#"panic!("non-exhaustive match")"#));
    }

    #[test]
    fn collapses_single_tuple_binding_match() {
        let source = r#"
pub fn first<A, B>(p: (A, B)) -> A
where
    A: Clone + 'static,
    B: Clone + 'static,
{
    match p.clone() {
        (x, _) => { x.clone() },
        _ => { panic!("non-exhaustive match") },
    }
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.removed_panic_arms, 1);
        assert_eq!(analysis.collapsed_single_arm_matches, 1);
        assert!(printed.contains("let (x, _) = p.clone();"));
        assert!(!printed.contains("match p.clone()"));
        assert!(!printed.contains(r#"panic!("non-exhaustive match")"#));
    }

    #[test]
    fn keeps_single_constructor_match_shape() {
        let source = r#"
#[derive(Clone)]
pub enum Single<A> {
    Single(A),
}

pub fn unbox<A>(x: Single<A>) -> A
where
    A: Clone + 'static,
{
    match x {
        Single::Single(y) => { y.clone() },
        _ => { panic!("non-exhaustive match") },
    }
}
"#;

        let (analysis, printed) = optimize_and_print(source);
        assert_eq!(analysis.removed_panic_arms, 1);
        assert_eq!(analysis.collapsed_single_arm_matches, 0);
        assert!(printed.contains("match x"));
        assert!(printed.contains("Single::Single(y)"));
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
