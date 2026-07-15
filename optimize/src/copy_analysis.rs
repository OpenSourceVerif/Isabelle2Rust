use std::collections::{HashMap, HashSet};

use rustlightast::*;

/// Result of the copy-analysis pass.
#[derive(Debug, Clone, Default)]
pub struct CopyAnalysis {
    pub copy_types: HashSet<String>,
}

/// Configuration for the copy-analysis pass.
#[derive(Debug, Clone, Copy, Default)]
pub struct CopyOptions {
    pub keep_unused_copy: bool,
}

type TypeEnv = HashMap<String, Type>;
type ItemId = Vec<String>;

#[derive(Debug, Clone)]
struct ModuleScope {
    module_path: Vec<String>,
    imports: HashMap<String, Vec<String>>,
}

impl ModuleScope {
    fn resolve_name_path(&self, name: &str) -> ItemId {
        if is_primitive_copy_type(name) {
            return vec![name.to_string()];
        }

        if let Some(path) = self.imports.get(name) {
            return path.clone();
        }

        let mut path = self.module_path.clone();
        path.push(name.to_string());
        path
    }

    fn resolve_segments(&self, segments: &[String]) -> ItemId {
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
}

#[derive(Debug, Clone)]
struct FieldInfo {
    name: String,
    ty: Type,
}

#[derive(Debug, Clone)]
struct VariantInfo {
    name: String,
    fields: Vec<Type>,
}

#[derive(Debug, Clone)]
enum TypeDefKind {
    Struct(Vec<FieldInfo>),
    Enum(Vec<VariantInfo>),
}

#[derive(Debug, Clone)]
struct TypeDef {
    generics: Vec<String>,
    kind: TypeDefKind,
    scope: ModuleScope,
}

#[derive(Debug, Clone)]
struct CopySpecialization {
    id: ItemId,
    name: String,
    upgraded_generics: HashSet<String>,
}

struct CopyContext {
    copy_types: HashSet<ItemId>,
    type_defs: HashMap<ItemId, TypeDef>,
    type_aliases: HashMap<ItemId, (Type, ModuleScope)>,
    variant_owners: HashMap<ItemId, Option<ItemId>>,
    functions: HashMap<ItemId, Type>,
    // Full signatures for C-Call: generic params + parameter types
    fn_sigs: HashMap<ItemId, (Vec<GenericParam>, Vec<Type>)>,
    copy_specializations: HashMap<ItemId, CopySpecialization>,
    generated_copy_specializations: HashSet<ItemId>,
}

/// Infer Copy data types for the Rust fragment generated from Isabelle/HOL,
/// add Copy derives, and remove redundant `.clone()` calls whose receiver has
/// a statically known Copy type.
///
/// This pass intentionally stays on the paper's copy-inference side of the
/// pipeline: it does not optimize borrow/reference expressions or method/impl
/// bodies, which belong to later optimization stages.
pub fn optimize_copy(module: &mut RustModule) -> CopyAnalysis {
    optimize_copy_with_options(module, CopyOptions::default())
}

pub fn optimize_copy_with_options(module: &mut RustModule, options: CopyOptions) -> CopyAnalysis {
    let module_path = vec!["crate".to_string(), module.name.clone()];
    let mut modules = [(module_path, module)];
    optimize_copy_modules_with_paths(&mut modules, options)
}

/// Infer and apply Copy optimizations across every parsed module in a package.
pub fn optimize_copy_modules(modules: &mut [&mut RustModule]) -> CopyAnalysis {
    let mut located_modules = modules
        .iter_mut()
        .map(|module| {
            (
                vec!["crate".to_string(), module.name.clone()],
                &mut **module,
            )
        })
        .collect::<Vec<_>>();
    optimize_copy_modules_with_paths(&mut located_modules, CopyOptions::default())
}

/// Package-level Copy inference with canonical module paths supplied by the
/// source-file discovery layer. All type and function identities are resolved
/// against their defining module and imports before any rewrite starts.
pub fn optimize_copy_modules_with_paths(
    modules: &mut [(Vec<String>, &mut RustModule)],
    options: CopyOptions,
) -> CopyAnalysis {
    let mut ctx = CopyContext::from_modules(modules);

    // Infer the package-wide fixed point before adding derives or rewriting
    // any body, so imported data types and callees see the same Copy facts.
    ctx.infer_copy_types();

    for (module_path, module) in modules.iter_mut() {
        ctx.apply_copy_derives(&mut module.items, module_path);
    }
    for (module_path, module) in modules.iter_mut() {
        ctx.add_copy_specializations(&mut module.items, module_path);
    }
    for (module_path, module) in modules.iter_mut() {
        ctx.rewrite_items(&mut module.items, module_path);
    }
    if !options.keep_unused_copy {
        ctx.prune_unused_copy_specializations_in_modules(modules);
    }

    CopyAnalysis {
        copy_types: ctx.public_copy_type_names(),
    }
}

impl CopyContext {
    fn from_modules(modules: &[(Vec<String>, &mut RustModule)]) -> Self {
        let mut ctx = Self {
            copy_types: primitive_copy_types()
                .into_iter()
                .map(|name| vec![name.to_string()])
                .collect(),
            type_defs: HashMap::new(),
            type_aliases: HashMap::new(),
            variant_owners: HashMap::new(),
            functions: HashMap::new(),
            fn_sigs: HashMap::new(),
            copy_specializations: HashMap::new(),
            generated_copy_specializations: HashSet::new(),
        };

        for (module_path, module) in modules {
            ctx.collect_items(&module.items, module_path);
        }

        ctx
    }

    fn collect_items(&mut self, items: &[Item], module_path: &[String]) {
        let scope = ModuleScope {
            module_path: module_path.to_vec(),
            imports: collect_imports(items),
        };
        for item in items {
            self.collect_item(item, &scope);
        }
    }

    fn collect_item(&mut self, item: &Item, scope: &ModuleScope) {
        match item {
            Item::Struct(def) => {
                let id = item_id(scope, &def.name);
                self.type_defs.insert(
                    id,
                    TypeDef {
                        generics: def
                            .generics
                            .iter()
                            .map(|generic| generic.name.clone())
                            .collect(),
                        kind: TypeDefKind::Struct(
                            def.fields
                                .iter()
                                .map(|field| FieldInfo {
                                    name: field.name.clone(),
                                    ty: field.ty.clone(),
                                })
                                .collect(),
                        ),
                        scope: scope.clone(),
                    },
                );
            }
            Item::Enum(def) => {
                let owner_id = item_id(scope, &def.name);
                for variant in &def.variants {
                    let mut variant_id = owner_id.clone();
                    variant_id.push(variant.name.clone());
                    self.insert_variant_owner(variant_id, &owner_id);
                }

                self.type_defs.insert(
                    owner_id,
                    TypeDef {
                        generics: def
                            .generics
                            .iter()
                            .map(|generic| generic.name.clone())
                            .collect(),
                        kind: TypeDefKind::Enum(
                            def.variants
                                .iter()
                                .map(|variant| VariantInfo {
                                    name: variant.name.clone(),
                                    fields: variant.data.clone().unwrap_or_default(),
                                })
                                .collect(),
                        ),
                        scope: scope.clone(),
                    },
                );
            }
            Item::TypeAlias(alias) => {
                self.type_aliases.insert(
                    item_id(scope, &alias.name),
                    (alias.target.clone(), scope.clone()),
                );
            }
            Item::Function(function) => {
                let id = item_id(scope, &function.name);
                self.functions
                    .insert(id.clone(), function.return_type.clone());
                self.fn_sigs.insert(
                    id,
                    (
                        function.generics.clone(),
                        function.params.iter().map(|p| p.ty.clone()).collect(),
                    ),
                );
            }
            Item::Mod(module) => {
                let mut nested_path = scope.module_path.clone();
                nested_path.push(module.name.clone());
                self.collect_items(&module.items, &nested_path);
            }
            _ => {}
        }
    }

    fn insert_variant_owner(&mut self, variant_id: ItemId, owner_id: &ItemId) {
        self.variant_owners
            .entry(variant_id)
            .and_modify(|existing| {
                if existing.as_ref() != Some(owner_id) {
                    *existing = None;
                }
            })
            .or_insert_with(|| Some(owner_id.clone()));
    }

    fn infer_copy_types(&mut self) {
        let mut changed = true;

        // Type aliases and algebraic data types can be mutually dependent, so
        // compute the least fixed point of "all contained fields are Copy".
        while changed {
            changed = false;

            for (name, (target, scope)) in &self.type_aliases {
                if !self.copy_types.contains(name)
                    && self.type_is_copy_in_scope(target, scope, &HashSet::new())
                {
                    self.copy_types.insert(name.clone());
                    changed = true;
                }
            }

            for (name, def) in &self.type_defs {
                if self.copy_types.contains(name) {
                    continue;
                }

                if self.type_def_is_copy(def) {
                    self.copy_types.insert(name.clone());
                    changed = true;
                }
            }
        }
    }

    fn type_def_is_copy(&self, def: &TypeDef) -> bool {
        let env = def.generics.iter().cloned().collect::<HashSet<_>>();

        match &def.kind {
            TypeDefKind::Struct(fields) => fields
                .iter()
                .all(|field| self.type_is_copy_in_scope(&field.ty, &def.scope, &env)),
            TypeDefKind::Enum(variants) => variants.iter().all(|variant| {
                variant
                    .fields
                    .iter()
                    .all(|ty| self.type_is_copy_in_scope(ty, &def.scope, &env))
            }),
        }
    }

    fn type_is_copy_in_scope(
        &self,
        ty: &Type,
        scope: &ModuleScope,
        copy_generics: &HashSet<String>,
    ) -> bool {
        match ty {
            Type::Named(name) => {
                copy_generics.contains(name)
                    || self.copy_types.contains(&scope.resolve_name_path(name))
            }
            Type::Path(path) => self.copy_types.contains(&scope.resolve_segments(path)),
            Type::Generic(name, params) => {
                self.copy_types.contains(&scope.resolve_name_path(name))
                    && params
                        .iter()
                        .all(|param| self.type_is_copy_in_scope(param, scope, copy_generics))
            }
            Type::Tuple(types) => types
                .iter()
                .all(|ty| self.type_is_copy_in_scope(ty, scope, copy_generics)),
            Type::Array(inner, _) => self.type_is_copy_in_scope(inner, scope, copy_generics),
            Type::Unit | Type::Never => true,
            Type::Reference(_, _, _) => false,
            Type::CallableTrait(_) => false,
            Type::Slice(_) => false,
        }
    }

    fn public_copy_type_names(&self) -> HashSet<String> {
        let mut definitions_by_name: HashMap<&str, Vec<&ItemId>> = HashMap::new();
        for id in self.type_defs.keys().chain(self.type_aliases.keys()) {
            if let Some(name) = id.last() {
                definitions_by_name.entry(name).or_default().push(id);
            }
        }

        let mut names = primitive_copy_types()
            .into_iter()
            .map(str::to_string)
            .collect::<HashSet<_>>();
        for (name, ids) in definitions_by_name {
            if ids.iter().all(|id| self.copy_types.contains(*id)) {
                names.insert(name.to_string());
            }
        }
        names
    }

    fn apply_copy_derives(&self, items: &mut [Item], module_path: &[String]) {
        let scope = ModuleScope {
            module_path: module_path.to_vec(),
            imports: collect_imports(items),
        };
        for item in items {
            match item {
                Item::Struct(def) if self.copy_types.contains(&item_id(&scope, &def.name)) => {
                    ensure_item_comment(&mut def.docs, "// copy-optimized by inferred Copy derive");
                    ensure_clone_copy_derives(&mut def.derives);
                }
                Item::Enum(def) if self.copy_types.contains(&item_id(&scope, &def.name)) => {
                    ensure_item_comment(&mut def.docs, "// copy-optimized by inferred Copy derive");
                    ensure_clone_copy_derives(&mut def.derives);
                }
                Item::Mod(module) => {
                    let mut nested_path = scope.module_path.clone();
                    nested_path.push(module.name.clone());
                    self.apply_copy_derives(&mut module.items, &nested_path);
                }
                _ => {}
            }
        }
    }

    fn rewrite_items(&self, items: &mut [Item], module_path: &[String]) {
        let scope = ModuleScope {
            module_path: module_path.to_vec(),
            imports: collect_imports(items),
        };
        for item in items {
            self.rewrite_item(item, &scope);
        }
    }

    fn add_copy_specializations(&mut self, items: &mut Vec<Item>, module_path: &[String]) {
        let scope = ModuleScope {
            module_path: module_path.to_vec(),
            imports: collect_imports(items),
        };
        // Keep the Clone-constrained original API intact and append a Copy-only
        // overload with clone calls removed when the body proves this is valid.
        let mut existing_function_names = items
            .iter()
            .filter_map(|item| match item {
                Item::Function(function) => Some(function.name.clone()),
                _ => None,
            })
            .collect::<HashSet<_>>();

        let original_items = std::mem::take(items);
        for mut item in original_items {
            match &mut item {
                Item::Function(function) => {
                    let original_name = function.name.clone();
                    let original_id = item_id(&scope, &original_name);
                    let specialization = self.copy_specialization_for_function(
                        function,
                        &scope,
                        &mut existing_function_names,
                    );
                    items.push(item);
                    if let Some((specialization, upgraded_generics)) = specialization {
                        let specialization_id = item_id(&scope, &specialization.name);
                        // Register the _copy variant's signature so C-Call can redirect to it.
                        self.copy_specializations.insert(
                            original_id,
                            CopySpecialization {
                                id: specialization_id.clone(),
                                name: specialization.name.clone(),
                                upgraded_generics,
                            },
                        );
                        self.generated_copy_specializations
                            .insert(specialization_id.clone());
                        self.functions.insert(
                            specialization_id.clone(),
                            specialization.return_type.clone(),
                        );
                        self.fn_sigs.insert(
                            specialization_id,
                            (
                                specialization.generics.clone(),
                                specialization.params.iter().map(|p| p.ty.clone()).collect(),
                            ),
                        );
                        items.push(Item::Function(specialization));
                    }
                }
                Item::Mod(module) => {
                    let mut nested_path = scope.module_path.clone();
                    nested_path.push(module.name.clone());
                    self.add_copy_specializations(&mut module.items, &nested_path);
                    items.push(item);
                }
                _ => items.push(item),
            }
        }
    }

    fn prune_unused_copy_specializations_in_modules(
        &self,
        modules: &mut [(Vec<String>, &mut RustModule)],
    ) {
        if self.generated_copy_specializations.is_empty() {
            return;
        }

        let mut calls_by_function: HashMap<ItemId, HashSet<ItemId>> = HashMap::new();
        let mut pending = HashSet::new();
        for (module_path, module) in modules.iter() {
            self.collect_specialization_calls(
                &module.items,
                module_path,
                &mut calls_by_function,
                &mut pending,
            );
        }

        let mut reachable = HashSet::new();
        let mut worklist = pending.into_iter().collect::<Vec<_>>();
        while let Some(id) = worklist.pop() {
            if reachable.insert(id.clone()) {
                if let Some(calls) = calls_by_function.get(&id) {
                    worklist.extend(calls.iter().cloned());
                }
            }
        }

        for (module_path, module) in modules.iter_mut() {
            self.retain_reachable_specializations(&mut module.items, module_path, &reachable);
        }
    }

    fn copy_specialization_for_function(
        &self,
        function: &FunctionDef,
        scope: &ModuleScope,
        existing_names: &mut HashSet<String>,
    ) -> Option<(FunctionDef, HashSet<String>)> {
        if function.name.ends_with("_copy") {
            return None;
        }

        let clone_generics = function
            .generics
            .iter()
            .filter(|generic| has_bound(generic, "Clone") && !has_bound(generic, "Copy"))
            .map(|generic| generic.name.clone())
            .collect::<HashSet<_>>();

        if clone_generics.is_empty() {
            return None;
        }

        let env = function_type_env(function);

        let mut copy_bound_candidates = HashSet::new();
        let copy_generics = generic_names_with_bound(function, "Copy");
        self.collect_copy_bound_candidates(
            &function.body,
            &env,
            scope,
            &clone_generics,
            &copy_generics,
            &mut copy_bound_candidates,
        );

        if copy_bound_candidates.is_empty() {
            return None;
        }

        let mut specialized = function.clone();
        specialized.name = fresh_copy_specialization_name(&function.name, existing_names);
        ensure_function_comment(
            &mut specialized,
            "// copy-optimized by Copy-specialized bounds",
        );

        for generic in &mut specialized.generics {
            if copy_bound_candidates.contains(&generic.name) {
                generic.bounds.retain(|bound| bound != "Clone");
                if !has_bound(generic, "Copy") {
                    generic.bounds.push("Copy".to_string());
                }
            }
        }

        let mut specialized_env = function_type_env(&specialized);
        let copy_generics = generic_names_with_bound(&specialized, "Copy");

        self.rewrite_block(
            &mut specialized.body,
            &mut specialized_env,
            scope,
            &copy_generics,
        );

        Some((specialized, copy_bound_candidates))
    }

    fn rewrite_item(&self, item: &mut Item, scope: &ModuleScope) {
        match item {
            Item::Function(function) => self.rewrite_function(function, scope),
            Item::Mod(module) => {
                let mut nested_path = scope.module_path.clone();
                nested_path.push(module.name.clone());
                self.rewrite_items(&mut module.items, &nested_path);
            }
            _ => {}
        }
    }

    fn rewrite_function(&self, function: &mut FunctionDef, scope: &ModuleScope) {
        let mut env = function_type_env(function);

        let copy_generics = generic_names_with_bound(function, "Copy");

        self.rewrite_block(&mut function.body, &mut env, scope, &copy_generics);
    }

    fn rewrite_block(
        &self,
        block: &mut Block,
        env: &mut TypeEnv,
        scope: &ModuleScope,
        copy_generics: &HashSet<String>,
    ) {
        for stmt in &mut block.stmts {
            match stmt {
                Statement::Let(let_stmt) => {
                    if let Some(init) = &mut let_stmt.init {
                        self.rewrite_expr(init, env, scope, copy_generics);
                    }

                    // Keep the local type environment precise enough for later
                    // field access and pattern-bound clone receivers.
                    let inferred_ty = let_stmt.ty.clone().or_else(|| {
                        let_stmt
                            .init
                            .as_ref()
                            .and_then(|init| self.infer_expr_type(init, env, scope))
                    });

                    if let Some(ty) = inferred_ty {
                        if is_binding_ident(&let_stmt.name) {
                            env.insert(let_stmt.name.clone(), ty);
                        } else {
                            self.bind_pattern_types(&let_stmt.name, &ty, env, scope);
                        }
                    }
                }
                Statement::Expr(expr) => self.rewrite_expr(expr, env, scope, copy_generics),
                Statement::Item(item) => self.rewrite_item(item, scope),
                Statement::Continue | Statement::Break | Statement::Comment(_) => {}
            }
        }

        if let Some(expr) = &mut block.expr {
            self.rewrite_expr(expr, env, scope, copy_generics);
        }
    }

    fn rewrite_expr(
        &self,
        expr: &mut Expr,
        env: &mut TypeEnv,
        scope: &ModuleScope,
        copy_generics: &HashSet<String>,
    ) {
        match expr {
            Expr::Array(items) | Expr::Tuple(items) => {
                for item in items {
                    self.rewrite_expr(item, env, scope, copy_generics);
                }
            }
            Expr::Call(callee, args) => {
                self.rewrite_expr(callee, env, scope, copy_generics);
                for arg in &mut *args {
                    self.rewrite_expr(arg, env, scope, copy_generics);
                }
                // C-Call: redirect g(ē) → g_copy(ē) when its upgraded bounds are Copy.
                if let Some(new_callee) =
                    self.try_copy_call(callee, args, env, scope, copy_generics)
                {
                    **callee = new_callee;
                }
            }
            Expr::MethodCall(receiver, method, args) => {
                self.rewrite_expr(receiver, env, scope, copy_generics);
                for arg in &mut *args {
                    self.rewrite_expr(arg, env, scope, copy_generics);
                }

                if method == "clone"
                    && args.is_empty()
                    && self
                        .infer_expr_type(receiver, env, scope)
                        .is_some_and(|ty| self.type_is_copy_in_scope(&ty, scope, copy_generics))
                {
                    // For Copy receivers, `x.clone()` is semantically just `x`.
                    *expr = receiver.as_ref().clone();
                }
            }
            Expr::Block(block) => {
                let mut block_env = env.clone();
                self.rewrite_block(block, &mut block_env, scope, copy_generics);
            }
            Expr::If {
                condition,
                then_branch,
                else_branch,
            } => {
                self.rewrite_expr(condition, env, scope, copy_generics);

                let mut then_env = env.clone();
                self.rewrite_block(then_branch, &mut then_env, scope, copy_generics);

                if let Some(else_branch) = else_branch {
                    let mut else_env = env.clone();
                    self.rewrite_block(else_branch, &mut else_env, scope, copy_generics);
                }
            }
            Expr::IfLet {
                pattern,
                value,
                then_branch,
                else_branch,
            } => {
                self.rewrite_expr(value, env, scope, copy_generics);

                let mut then_env = env.clone();
                if let Some(value_ty) = self.infer_expr_type(value, env, scope) {
                    self.bind_pattern_types(pattern, &value_ty, &mut then_env, scope);
                }
                self.rewrite_block(then_branch, &mut then_env, scope, copy_generics);

                if let Some(else_branch) = else_branch {
                    let mut else_env = env.clone();
                    self.rewrite_block(else_branch, &mut else_env, scope, copy_generics);
                }
            }
            Expr::Match { expr, arms } => {
                self.rewrite_expr(expr, env, scope, copy_generics);
                let scrutinee_ty = self.infer_expr_type(expr, env, scope);

                for arm in arms {
                    let mut arm_env = env.clone();

                    if let Some(ty) = &scrutinee_ty {
                        self.bind_pattern_types(&arm.pattern, ty, &mut arm_env, scope);
                    }
                    if let Some(guard) = &mut arm.guard {
                        self.rewrite_expr(guard, &mut arm_env, scope, copy_generics);
                    }

                    self.rewrite_block(&mut arm.body, &mut arm_env, scope, copy_generics);
                }
            }
            Expr::Closure(params, body, _) | Expr::TypedClosure(params, _, body, _) => {
                let mut closure_env = env.clone();
                for param in params {
                    let name = closure_param_name(param);
                    if !is_binding_ident(&name) {
                        continue;
                    }
                    if let Some(ty) = closure_param_type(param) {
                        closure_env.insert(name, ty);
                    } else {
                        closure_env.remove(&name);
                    }
                }
                self.rewrite_expr(body, &mut closure_env, scope, copy_generics);
            }
            Expr::Parenthesized(inner) | Expr::Cast(inner, _) => {
                self.rewrite_expr(inner, env, scope, copy_generics)
            }
            Expr::BinaryOp(left, _, right) => {
                self.rewrite_expr(left, env, scope, copy_generics);
                self.rewrite_expr(right, env, scope, copy_generics);
            }
            Expr::UnaryOp(_, inner) => self.rewrite_expr(inner, env, scope, copy_generics),
            // Constructs outside the generated fragment are left unchanged here.
            Expr::Ident(_)
            | Expr::Macro(_)
            | Expr::Path(_, _)
            | Expr::Literal(_)
            | Expr::Loop(_)
            | Expr::Await(_)
            | Expr::BuilderChain(_)
            | Expr::Unsafe(_)
            | Expr::Reference(_, _, _)
            | Expr::Index(_, _)
            | Expr::Assign(_, _) => {}
        }
    }

    fn collect_copy_bound_candidates(
        &self,
        block: &Block,
        env: &TypeEnv,
        scope: &ModuleScope,
        clone_generics: &HashSet<String>,
        copy_generics: &HashSet<String>,
        out: &mut HashSet<String>,
    ) {
        let mut required_copy_env = copy_generics.clone();
        required_copy_env.extend(clone_generics.iter().cloned());
        // A generic is a candidate only if every clone receiver containing it
        // would become Copy after replacing tracked Clone bounds by Copy.
        self.collect_clone_demands(
            block,
            env,
            scope,
            clone_generics,
            Some(&required_copy_env),
            out,
        );
    }

    fn collect_clone_demands(
        &self,
        block: &Block,
        env: &TypeEnv,
        scope: &ModuleScope,
        tracked_generics: &HashSet<String>,
        required_copy_env: Option<&HashSet<String>>,
        out: &mut HashSet<String>,
    ) {
        let mut block_env = env.clone();

        for stmt in &block.stmts {
            match stmt {
                Statement::Let(let_stmt) => {
                    if let Some(init) = &let_stmt.init {
                        self.collect_clone_demands_expr(
                            init,
                            &block_env,
                            scope,
                            tracked_generics,
                            required_copy_env,
                            out,
                        );
                    }

                    let inferred_ty = let_stmt.ty.clone().or_else(|| {
                        let_stmt
                            .init
                            .as_ref()
                            .and_then(|init| self.infer_expr_type(init, &block_env, scope))
                    });

                    if let Some(ty) = inferred_ty {
                        if is_binding_ident(&let_stmt.name) {
                            block_env.insert(let_stmt.name.clone(), ty);
                        } else {
                            self.bind_pattern_types(&let_stmt.name, &ty, &mut block_env, scope);
                        }
                    }
                }
                Statement::Expr(expr) => self.collect_clone_demands_expr(
                    expr,
                    &block_env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    out,
                ),
                Statement::Item(_)
                | Statement::Continue
                | Statement::Break
                | Statement::Comment(_) => {}
            }
        }

        if let Some(expr) = &block.expr {
            self.collect_clone_demands_expr(
                expr,
                &block_env,
                scope,
                tracked_generics,
                required_copy_env,
                out,
            );
        }
    }

    fn collect_clone_demands_expr(
        &self,
        expr: &Expr,
        env: &TypeEnv,
        scope: &ModuleScope,
        tracked_generics: &HashSet<String>,
        required_copy_env: Option<&HashSet<String>>,
        out: &mut HashSet<String>,
    ) {
        match expr {
            Expr::Array(items) | Expr::Tuple(items) => {
                for item in items {
                    self.collect_clone_demands_expr(
                        item,
                        env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        out,
                    );
                }
            }
            Expr::Call(callee, args) => {
                self.collect_clone_demands_expr(
                    callee,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                for arg in args {
                    self.collect_clone_demands_expr(
                        arg,
                        env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        out,
                    );
                }
            }
            Expr::MethodCall(receiver, method, args) => {
                self.collect_clone_demands_expr(
                    receiver,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                for arg in args {
                    self.collect_clone_demands_expr(
                        arg,
                        env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        out,
                    );
                }

                if method == "clone" && args.is_empty() {
                    if let Some(ty) = self.infer_expr_type(receiver, env, scope) {
                        let mut names = HashSet::new();
                        generic_names_in_type(&ty, &mut names);
                        names.retain(|name| tracked_generics.contains(name));

                        let admissible = required_copy_env
                            .map(|copy_env| self.type_is_copy_in_scope(&ty, scope, copy_env))
                            .unwrap_or(true);

                        if admissible {
                            out.extend(names);
                        }
                    }
                }
            }
            Expr::Block(block) => {
                self.collect_clone_demands(
                    block,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
            }
            Expr::If {
                condition,
                then_branch,
                else_branch,
            } => {
                self.collect_clone_demands_expr(
                    condition,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                self.collect_clone_demands(
                    then_branch,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                if let Some(else_branch) = else_branch {
                    self.collect_clone_demands(
                        else_branch,
                        env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        out,
                    );
                }
            }
            Expr::IfLet {
                pattern,
                value,
                then_branch,
                else_branch,
            } => {
                self.collect_clone_demands_expr(
                    value,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                let mut then_env = env.clone();
                if let Some(value_ty) = self.infer_expr_type(value, env, scope) {
                    self.bind_pattern_types(pattern, &value_ty, &mut then_env, scope);
                }
                self.collect_clone_demands(
                    then_branch,
                    &then_env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                if let Some(else_branch) = else_branch {
                    self.collect_clone_demands(
                        else_branch,
                        env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        out,
                    );
                }
            }
            Expr::Match { expr, arms } => {
                self.collect_clone_demands_expr(
                    expr,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                let scrutinee_ty = self.infer_expr_type(expr, env, scope);
                for arm in arms {
                    let mut arm_env = env.clone();
                    if let Some(ty) = &scrutinee_ty {
                        self.bind_pattern_types(&arm.pattern, ty, &mut arm_env, scope);
                    }
                    if let Some(guard) = &arm.guard {
                        self.collect_clone_demands_expr(
                            guard,
                            &arm_env,
                            scope,
                            tracked_generics,
                            required_copy_env,
                            out,
                        );
                    }
                    self.collect_clone_demands(
                        &arm.body,
                        &arm_env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        out,
                    );
                }
            }
            Expr::Parenthesized(inner) | Expr::Cast(inner, _) => self.collect_clone_demands_expr(
                inner,
                env,
                scope,
                tracked_generics,
                required_copy_env,
                out,
            ),
            Expr::BinaryOp(left, _, right) => {
                self.collect_clone_demands_expr(
                    left,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                self.collect_clone_demands_expr(
                    right,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
            }
            Expr::UnaryOp(_, inner) => self.collect_clone_demands_expr(
                inner,
                env,
                scope,
                tracked_generics,
                required_copy_env,
                out,
            ),
            // Clone calls under unsupported Rust constructs do not participate
            // in copy-specialization inference.
            Expr::Ident(_)
            | Expr::Macro(_)
            | Expr::Path(_, _)
            | Expr::Literal(_)
            | Expr::Loop(_)
            | Expr::Await(_)
            | Expr::Closure(_, _, _)
            | Expr::TypedClosure(_, _, _, _)
            | Expr::BuilderChain(_)
            | Expr::Unsafe(_)
            | Expr::Reference(_, _, _)
            | Expr::Index(_, _)
            | Expr::Assign(_, _) => {}
        }
    }

    // C-Call: if callee g has a _copy variant and every generic strengthened in
    // that variant resolves to a Copy type, return the _copy variant name.
    fn try_copy_call(
        &self,
        callee: &Expr,
        args: &[Expr],
        env: &TypeEnv,
        scope: &ModuleScope,
        copy_generics: &HashSet<String>,
    ) -> Option<Expr> {
        let fn_id = self.resolve_callee_id(callee, env, scope)?;
        let fn_name = fn_id.last()?;

        // Already a _copy variant — don't chain-redirect.
        if fn_name.ends_with("_copy") {
            return None;
        }

        let specialization = self.copy_specializations.get(&fn_id)?;
        let upgraded_generics = &specialization.upgraded_generics;

        let (generics, param_types) = self.fn_sigs.get(&fn_id)?;

        if args.len() != param_types.len() {
            return None;
        }

        let callee_generic_names: HashSet<String> =
            generics.iter().map(|g| g.name.clone()).collect();

        // Fast path: we're already inside a copy-specialized context that
        // covers every generic strengthened by the callee.  This handles
        // recursive calls like `list_head(List::Nil)` inside `list_head_copy`
        // where the argument type is opaque (no type-arg info to unify on).
        if upgraded_generics
            .iter()
            .all(|generic| copy_generics.contains(generic))
        {
            return Some(self.specialization_callee(callee, specialization, scope));
        }

        let arg_types: Vec<Type> = args
            .iter()
            .map(|a| self.infer_expr_type(a, env, scope))
            .collect::<Option<_>>()?;

        let mut subst = HashMap::new();
        for (formal, actual) in param_types.iter().zip(arg_types.iter()) {
            if !unify_type(formal, actual, &callee_generic_names, &mut subst) {
                return None;
            }
        }

        for alpha in upgraded_generics {
            let concrete = subst.get(alpha)?;
            if !self.type_is_copy_in_scope(concrete, scope, copy_generics) {
                return None;
            }
        }

        Some(self.specialization_callee(callee, specialization, scope))
    }

    fn specialization_callee(
        &self,
        original: &Expr,
        specialization: &CopySpecialization,
        scope: &ModuleScope,
    ) -> Expr {
        if matches!(original, Expr::Ident(_))
            && specialization.id[..specialization.id.len().saturating_sub(1)] == scope.module_path
        {
            Expr::Ident(specialization.name.clone())
        } else {
            Expr::Path(specialization.id.clone(), PathType::Namespace)
        }
    }

    fn resolve_callee_id(
        &self,
        callee: &Expr,
        env: &TypeEnv,
        scope: &ModuleScope,
    ) -> Option<ItemId> {
        let id = match callee {
            Expr::Ident(name) if env.contains_key(name) => return None,
            Expr::Ident(name) => scope.resolve_name_path(name),
            Expr::Path(path, PathType::Namespace) => scope.resolve_segments(path),
            Expr::Parenthesized(inner) => return self.resolve_callee_id(inner, env, scope),
            _ => return None,
        };
        self.fn_sigs.contains_key(&id).then_some(id)
    }

    fn infer_expr_type(&self, expr: &Expr, env: &TypeEnv, scope: &ModuleScope) -> Option<Type> {
        match expr {
            Expr::Ident(name) => env.get(name).cloned(),
            Expr::Path(path, PathType::Namespace) => self
                .owner_for_variant_path(path, scope)
                .map(Type::Path)
                .or_else(|| self.functions.get(&scope.resolve_segments(path)).cloned()),
            Expr::Path(path, PathType::Member) => self.infer_member_path_type(path, env, scope),
            Expr::Literal(Literal::Bool(_)) => Some(Type::Named("bool".to_string())),
            Expr::Literal(_) => None,
            Expr::Array(items) => {
                let first = items.first()?;
                let element_ty = self.infer_expr_type(first, env, scope)?;
                Some(Type::Array(Box::new(element_ty), items.len()))
            }
            Expr::Tuple(items) => {
                let mut types = Vec::new();
                for item in items {
                    types.push(self.infer_expr_type(item, env, scope)?);
                }

                if types.is_empty() {
                    Some(Type::Unit)
                } else {
                    Some(Type::Tuple(types))
                }
            }
            Expr::Call(callee, _) => self.infer_call_type(callee, env, scope),
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                self.infer_expr_type(receiver, env, scope)
            }
            Expr::Parenthesized(inner) => self.infer_expr_type(inner, env, scope),
            Expr::Cast(_, ty) => Some(ty.clone()),
            Expr::Block(block) => block
                .expr
                .as_ref()
                .and_then(|expr| self.infer_expr_type(expr, env, scope)),
            Expr::UnaryOp(op, inner) if op == "*" => {
                match self.infer_expr_type(inner, env, scope)? {
                    Type::Generic(name, mut params) if name == "Box" && params.len() == 1 => {
                        params.pop()
                    }
                    Type::Reference(inner, _, _) => Some(*inner),
                    _ => None,
                }
            }
            Expr::BinaryOp(_, op, _) if binary_op_returns_bool(op) => {
                Some(Type::Named("bool".to_string()))
            }
            _ => None,
        }
    }

    fn infer_call_type(&self, callee: &Expr, env: &TypeEnv, scope: &ModuleScope) -> Option<Type> {
        match callee {
            Expr::Ident(name) if env.contains_key(name) => None,
            Expr::Ident(name) => self
                .owner_for_variant_name(name, scope)
                .map(Type::Path)
                .or_else(|| self.functions.get(&scope.resolve_name_path(name)).cloned()),
            Expr::Path(path, PathType::Namespace) => self
                .owner_for_variant_path(path, scope)
                .map(Type::Path)
                .or_else(|| self.functions.get(&scope.resolve_segments(path)).cloned()),
            Expr::Parenthesized(inner) => self.infer_call_type(inner, env, scope),
            _ => None,
        }
    }

    fn infer_member_path_type(
        &self,
        path: &[String],
        env: &TypeEnv,
        scope: &ModuleScope,
    ) -> Option<Type> {
        let (head, tail) = path.split_first()?;
        let mut current_ty = env.get(head)?.clone();

        for member in tail {
            current_ty = self.field_type(&current_ty, member, scope)?;
        }

        Some(current_ty)
    }

    fn field_type(&self, ty: &Type, member: &str, scope: &ModuleScope) -> Option<Type> {
        let type_id = self.type_id_for_type(ty, scope)?;
        let def = self.type_defs.get(&type_id)?;
        let subst = type_substitution(def, ty);

        match &def.kind {
            TypeDefKind::Struct(fields) => fields.iter().find_map(|field| {
                if field.name == member {
                    Some(apply_type_subst(&field.ty, &subst))
                } else {
                    None
                }
            }),
            TypeDefKind::Enum(_) => None,
        }
    }

    fn bind_pattern_types(
        &self,
        pattern: &str,
        expected: &Type,
        env: &mut TypeEnv,
        scope: &ModuleScope,
    ) {
        let pattern = pattern.trim();
        if pattern.is_empty() || pattern == "_" || pattern == ".." {
            return;
        }

        // Pattern strings are kept lightweight in RustLightAST, so this routine
        // recovers just enough structure to bind identifiers to payload types.
        if let Some(inner) = strip_prefix_word(pattern, "box") {
            let inner_ty = match expected {
                Type::Generic(name, params) if name == "Box" && params.len() == 1 => &params[0],
                _ => expected,
            };
            self.bind_pattern_types(inner, inner_ty, env, scope);
            return;
        }

        let pattern = strip_binding_modifiers(pattern);

        if let Some(inner) = outer_parens_inner(pattern) {
            let parts = split_top_level_commas(inner);
            if parts.len() > 1 {
                if let Type::Tuple(types) = expected {
                    for (part, ty) in parts.iter().zip(types) {
                        self.bind_pattern_types(part, ty, env, scope);
                    }
                }
                return;
            }
        }

        if let Some((constructor, args)) = split_constructor_pattern(pattern) {
            if let Some(field_types) = self.pattern_payload_types(constructor, expected, scope) {
                for (arg, ty) in args.iter().zip(field_types.iter()) {
                    self.bind_pattern_types(arg, ty, env, scope);
                }
            }
            return;
        }

        if pattern.contains("::") || matches!(pattern, "true" | "false") {
            return;
        }

        if is_binding_ident(pattern) {
            env.insert(pattern.to_string(), expected.clone());
        }
    }

    fn pattern_payload_types(
        &self,
        constructor: &str,
        expected: &Type,
        scope: &ModuleScope,
    ) -> Option<Vec<Type>> {
        let variant_name = constructor
            .rsplit("::")
            .next()
            .unwrap_or(constructor)
            .trim();

        if let Some(expected_id) = self.type_id_for_type(expected, scope) {
            if let Some(def) = self.type_defs.get(&expected_id) {
                let subst = type_substitution(def, expected);
                match &def.kind {
                    TypeDefKind::Enum(variants) => {
                        if let Some(variant) =
                            variants.iter().find(|variant| variant.name == variant_name)
                        {
                            return Some(
                                variant
                                    .fields
                                    .iter()
                                    .map(|ty| apply_type_subst(ty, &subst))
                                    .collect(),
                            );
                        }
                    }
                    TypeDefKind::Struct(fields)
                        if expected_id.last().is_some_and(|name| name == variant_name)
                            || expected_id
                                .last()
                                .is_some_and(|name| name == constructor.trim()) =>
                    {
                        return Some(
                            fields
                                .iter()
                                .map(|field| apply_type_subst(&field.ty, &subst))
                                .collect(),
                        );
                    }
                    TypeDefKind::Struct(_) => {}
                }
            }
        }

        let owner = self.owner_for_constructor(constructor, scope)?;
        let def = self.type_defs.get(&owner)?;
        match &def.kind {
            TypeDefKind::Enum(variants) => variants
                .iter()
                .find(|variant| variant.name == variant_name)
                .map(|variant| variant.fields.clone()),
            TypeDefKind::Struct(fields) => {
                Some(fields.iter().map(|field| field.ty.clone()).collect())
            }
        }
    }

    fn owner_for_constructor(&self, constructor: &str, scope: &ModuleScope) -> Option<ItemId> {
        let parts = constructor
            .split("::")
            .map(str::trim)
            .filter(|part| !part.is_empty())
            .map(str::to_string)
            .collect::<Vec<_>>();

        let variant_id = scope.resolve_segments(&parts);
        self.variant_owners.get(&variant_id).cloned().flatten()
    }

    fn owner_for_variant_path(&self, path: &[String], scope: &ModuleScope) -> Option<ItemId> {
        let variant_id = scope.resolve_segments(path);
        self.variant_owners.get(&variant_id).cloned().flatten()
    }

    fn owner_for_variant_name(&self, variant_name: &str, scope: &ModuleScope) -> Option<ItemId> {
        let variant_id = scope.resolve_name_path(variant_name);
        self.variant_owners.get(&variant_id).cloned().flatten()
    }

    fn type_id_for_type(&self, ty: &Type, scope: &ModuleScope) -> Option<ItemId> {
        match ty {
            Type::Named(name) | Type::Generic(name, _) => Some(scope.resolve_name_path(name)),
            Type::Path(path) => Some(scope.resolve_segments(path)),
            Type::Reference(inner, _, _) => self.type_id_for_type(inner, scope),
            _ => None,
        }
    }

    fn collect_specialization_calls(
        &self,
        items: &[Item],
        module_path: &[String],
        calls_by_function: &mut HashMap<ItemId, HashSet<ItemId>>,
        root_calls: &mut HashSet<ItemId>,
    ) {
        let scope = ModuleScope {
            module_path: module_path.to_vec(),
            imports: collect_imports(items),
        };

        for item in items {
            match item {
                Item::Function(function) => {
                    let id = item_id(&scope, &function.name);
                    let mut calls = HashSet::new();
                    collect_generated_calls_block(
                        &function.body,
                        &scope,
                        &self.generated_copy_specializations,
                        &mut calls,
                    );
                    if self.generated_copy_specializations.contains(&id) {
                        calls_by_function.insert(id, calls);
                    } else {
                        root_calls.extend(calls);
                    }
                }
                Item::Impl(impl_block) => {
                    for impl_item in &impl_block.items {
                        match impl_item {
                            ImplItem::Method(method) => collect_generated_calls_block(
                                &method.body,
                                &scope,
                                &self.generated_copy_specializations,
                                root_calls,
                            ),
                            ImplItem::AssocConst(_, _, expr) => collect_generated_calls_expr(
                                expr,
                                &scope,
                                &self.generated_copy_specializations,
                                root_calls,
                            ),
                            ImplItem::AssocType(_, _) => {}
                        }
                    }
                }
                Item::Const(const_def) => collect_generated_calls_expr(
                    &const_def.value,
                    &scope,
                    &self.generated_copy_specializations,
                    root_calls,
                ),
                Item::LazyStatic(lazy_static) => collect_generated_calls_block(
                    &lazy_static.init,
                    &scope,
                    &self.generated_copy_specializations,
                    root_calls,
                ),
                Item::Mod(module) => {
                    let mut nested_path = scope.module_path.clone();
                    nested_path.push(module.name.clone());
                    self.collect_specialization_calls(
                        &module.items,
                        &nested_path,
                        calls_by_function,
                        root_calls,
                    );
                }
                Item::Raw(_)
                | Item::Struct(_)
                | Item::Enum(_)
                | Item::Union(_)
                | Item::TypeAlias(_)
                | Item::Use(_) => {}
            }
        }
    }

    fn retain_reachable_specializations(
        &self,
        items: &mut Vec<Item>,
        module_path: &[String],
        reachable: &HashSet<ItemId>,
    ) {
        let scope = ModuleScope {
            module_path: module_path.to_vec(),
            imports: collect_imports(items),
        };

        for item in &mut *items {
            if let Item::Mod(module) = item {
                let mut nested_path = scope.module_path.clone();
                nested_path.push(module.name.clone());
                self.retain_reachable_specializations(&mut module.items, &nested_path, reachable);
            }
        }

        items.retain(|item| {
            let Item::Function(function) = item else {
                return true;
            };
            let id = item_id(&scope, &function.name);
            !self.generated_copy_specializations.contains(&id) || reachable.contains(&id)
        });
    }
}

fn item_id(scope: &ModuleScope, name: &str) -> ItemId {
    let mut id = scope.module_path.clone();
    id.push(name.to_string());
    id
}

fn primitive_copy_types() -> [&'static str; 16] {
    [
        "bool", "char", "u8", "u16", "u32", "u64", "u128", "i8", "i16", "i32", "i64", "i128",
        "usize", "isize", "f32", "f64",
    ]
}

fn is_primitive_copy_type(name: &str) -> bool {
    primitive_copy_types().contains(&name)
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

fn collect_generated_calls_item(
    item: &Item,
    scope: &ModuleScope,
    generated: &HashSet<ItemId>,
    out: &mut HashSet<ItemId>,
) {
    match item {
        Item::Function(function) => {
            collect_generated_calls_block(&function.body, scope, generated, out)
        }
        Item::Impl(impl_block) => {
            for impl_item in &impl_block.items {
                match impl_item {
                    ImplItem::Method(method) => {
                        collect_generated_calls_block(&method.body, scope, generated, out);
                    }
                    ImplItem::AssocConst(_, _, expr) => {
                        collect_generated_calls_expr(expr, scope, generated, out);
                    }
                    ImplItem::AssocType(_, _) => {}
                }
            }
        }
        Item::Const(const_def) => {
            collect_generated_calls_expr(&const_def.value, scope, generated, out)
        }
        Item::LazyStatic(lazy_static) => {
            collect_generated_calls_block(&lazy_static.init, scope, generated, out);
        }
        Item::Mod(module) => {
            let mut nested_path = scope.module_path.clone();
            nested_path.push(module.name.clone());
            let nested_scope = ModuleScope {
                module_path: nested_path,
                imports: collect_imports(&module.items),
            };
            for nested_item in &module.items {
                collect_generated_calls_item(nested_item, &nested_scope, generated, out);
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

fn collect_generated_calls_block(
    block: &Block,
    scope: &ModuleScope,
    generated: &HashSet<ItemId>,
    out: &mut HashSet<ItemId>,
) {
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &let_stmt.init {
                    collect_generated_calls_expr(init, scope, generated, out);
                }
            }
            Statement::Expr(expr) => collect_generated_calls_expr(expr, scope, generated, out),
            Statement::Item(item) => collect_generated_calls_item(item, scope, generated, out),
            Statement::Continue | Statement::Break | Statement::Comment(_) => {}
        }
    }

    if let Some(expr) = &block.expr {
        collect_generated_calls_expr(expr, scope, generated, out);
    }
}

fn collect_generated_calls_expr(
    expr: &Expr,
    scope: &ModuleScope,
    generated: &HashSet<ItemId>,
    out: &mut HashSet<ItemId>,
) {
    match expr {
        Expr::Call(callee, args) => {
            let callee_id = match callee.as_ref() {
                Expr::Ident(name) => Some(scope.resolve_name_path(name)),
                Expr::Path(path, PathType::Namespace) => Some(scope.resolve_segments(path)),
                _ => None,
            };
            if let Some(id) = callee_id.filter(|id| generated.contains(id)) {
                out.insert(id);
            }
            collect_generated_calls_expr(callee, scope, generated, out);
            for arg in args {
                collect_generated_calls_expr(arg, scope, generated, out);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            collect_generated_calls_expr(receiver, scope, generated, out);
            for arg in args {
                collect_generated_calls_expr(arg, scope, generated, out);
            }
        }
        Expr::Array(items) | Expr::Tuple(items) => {
            for item in items {
                collect_generated_calls_expr(item, scope, generated, out);
            }
        }
        Expr::Block(block) => {
            collect_generated_calls_block(block, scope, generated, out);
        }
        Expr::Loop(block) | Expr::Unsafe(block) => {
            collect_generated_calls_block(block, scope, generated, out);
        }
        Expr::Closure(_, body, _)
        | Expr::TypedClosure(_, _, body, _)
        | Expr::Await(body)
        | Expr::Parenthesized(body)
        | Expr::Cast(body, _) => {
            collect_generated_calls_expr(body, scope, generated, out);
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            collect_generated_calls_expr(condition, scope, generated, out);
            collect_generated_calls_block(then_branch, scope, generated, out);
            if let Some(else_branch) = else_branch {
                collect_generated_calls_block(else_branch, scope, generated, out);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            collect_generated_calls_expr(value, scope, generated, out);
            collect_generated_calls_block(then_branch, scope, generated, out);
            if let Some(else_branch) = else_branch {
                collect_generated_calls_block(else_branch, scope, generated, out);
            }
        }
        Expr::Match { expr, arms } => {
            collect_generated_calls_expr(expr, scope, generated, out);
            for arm in arms {
                if let Some(guard) = &arm.guard {
                    collect_generated_calls_expr(guard, scope, generated, out);
                }
                collect_generated_calls_block(&arm.body, scope, generated, out);
            }
        }
        Expr::Reference(inner, _, _) | Expr::UnaryOp(_, inner) => {
            collect_generated_calls_expr(inner, scope, generated, out);
        }
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            collect_generated_calls_expr(left, scope, generated, out);
            collect_generated_calls_expr(right, scope, generated, out);
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    collect_generated_calls_expr(closure, scope, generated, out);
                }
            }
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }
}

fn ensure_clone_copy_derives(derives: &mut Vec<String>) {
    if !derives.iter().any(|derive| derive == "Clone") {
        derives.push("Clone".to_string());
    }

    if derives.iter().any(|derive| derive == "Copy") {
        return;
    }

    let insert_at = derives
        .iter()
        .position(|derive| derive == "Clone")
        .map_or(derives.len(), |idx| idx + 1);
    derives.insert(insert_at, "Copy".to_string());
}

fn ensure_item_comment(docs: &mut Vec<String>, comment: &str) {
    if !docs.iter().any(|doc| doc.trim() == comment) {
        docs.push(comment.to_string());
    }
}

fn ensure_function_comment(function: &mut FunctionDef, comment: &str) {
    if !function.docs.iter().any(|doc| doc.trim() == comment) {
        function.docs.push(comment.to_string());
    }
}

fn has_bound(generic: &GenericParam, bound: &str) -> bool {
    generic.bounds.iter().any(|candidate| candidate == bound)
}

fn generic_names_with_bound(function: &FunctionDef, bound: &str) -> HashSet<String> {
    function
        .generics
        .iter()
        .filter(|generic| has_bound(generic, bound))
        .map(|generic| generic.name.clone())
        .collect()
}

fn fresh_copy_specialization_name(base: &str, existing_names: &mut HashSet<String>) -> String {
    let first = format!("{base}_copy");
    if existing_names.insert(first.clone()) {
        return first;
    }

    let mut suffix = 2usize;
    loop {
        let candidate = format!("{base}_copy{suffix}");
        if existing_names.insert(candidate.clone()) {
            return candidate;
        }
        suffix += 1;
    }
}

fn closure_param_name(param: &str) -> String {
    param
        .trim_start_matches("mut ")
        .split(':')
        .next()
        .unwrap_or(param)
        .trim()
        .to_string()
}

fn closure_param_type(param: &str) -> Option<Type> {
    let ty = param.split_once(':')?.1.trim();
    parse_simple_type(ty)
}

fn parse_simple_type(ty: &str) -> Option<Type> {
    let ty = ty.trim();
    if let Some(inner) = ty.strip_prefix('&') {
        let inner = inner.trim_start_matches("mut ").trim();
        return parse_simple_type(inner).map(|ty| Type::Reference(Box::new(ty), true, false));
    }

    if ty
        .chars()
        .all(|ch| ch == '_' || ch == ':' || ch.is_ascii_alphanumeric())
    {
        return Some(if ty.contains("::") {
            Type::Path(ty.split("::").map(str::to_string).collect())
        } else {
            Type::Named(ty.to_string())
        });
    }

    None
}

fn type_substitution(def: &TypeDef, ty: &Type) -> HashMap<String, Type> {
    match ty {
        Type::Generic(_, params) if params.len() == def.generics.len() => def
            .generics
            .iter()
            .cloned()
            .zip(params.iter().cloned())
            .collect(),
        _ => HashMap::new(),
    }
}

fn apply_type_subst(ty: &Type, subst: &HashMap<String, Type>) -> Type {
    match ty {
        Type::Named(name) => subst
            .get(name)
            .cloned()
            .unwrap_or_else(|| Type::Named(name.clone())),
        Type::Generic(name, params) => Type::Generic(
            name.clone(),
            params
                .iter()
                .map(|param| apply_type_subst(param, subst))
                .collect(),
        ),
        Type::Tuple(types) => Type::Tuple(
            types
                .iter()
                .map(|param| apply_type_subst(param, subst))
                .collect(),
        ),
        Type::Array(inner, len) => Type::Array(Box::new(apply_type_subst(inner, subst)), *len),
        Type::Reference(inner, is_ref, mutable) => {
            Type::Reference(Box::new(apply_type_subst(inner, subst)), *is_ref, *mutable)
        }
        Type::Slice(inner) => Type::Slice(Box::new(apply_type_subst(inner, subst))),
        Type::CallableTrait(callable) => Type::CallableTrait(CallableTraitType {
            qualifier: callable.qualifier.clone(),
            trait_name: callable.trait_name.clone(),
            args: callable
                .args
                .iter()
                .map(|arg| apply_type_subst(arg, subst))
                .collect(),
            return_type: Box::new(apply_type_subst(&callable.return_type, subst)),
        }),
        Type::Path(_) | Type::Unit | Type::Never => ty.clone(),
    }
}

fn generic_names_in_type(ty: &Type, out: &mut HashSet<String>) {
    match ty {
        Type::Named(name) => {
            if name
                .chars()
                .next()
                .is_some_and(|ch| ch.is_ascii_uppercase())
            {
                out.insert(name.clone());
            }
        }
        Type::Path(_) | Type::Unit | Type::Never => {}
        Type::Generic(_, params) | Type::Tuple(params) => {
            for param in params {
                generic_names_in_type(param, out);
            }
        }
        Type::Reference(inner, _, _) | Type::Slice(inner) | Type::Array(inner, _) => {
            generic_names_in_type(inner, out);
        }
        Type::CallableTrait(callable) => {
            for arg in &callable.args {
                generic_names_in_type(arg, out);
            }
            generic_names_in_type(&callable.return_type, out);
        }
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

fn binary_op_returns_bool(op: &str) -> bool {
    matches!(op, "==" | "!=" | "<" | "<=" | ">" | ">=" | "&&" | "||")
}

fn strip_prefix_word<'a>(input: &'a str, word: &str) -> Option<&'a str> {
    let rest = input.strip_prefix(word)?;
    if rest.starts_with(char::is_whitespace) {
        Some(rest.trim_start())
    } else {
        None
    }
}

fn strip_binding_modifiers(mut input: &str) -> &str {
    loop {
        let trimmed = input.trim_start();
        if let Some(rest) = strip_prefix_word(trimmed, "ref") {
            input = rest;
        } else if let Some(rest) = strip_prefix_word(trimmed, "mut") {
            input = rest;
        } else {
            return trimmed;
        }
    }
}

fn outer_parens_inner(input: &str) -> Option<&str> {
    if !input.starts_with('(') || !input.ends_with(')') {
        return None;
    }

    let mut depth = 0usize;
    for (idx, ch) in input.char_indices() {
        match ch {
            '(' => depth += 1,
            ')' => {
                depth = depth.checked_sub(1)?;
                if depth == 0 && idx != input.len() - 1 {
                    return None;
                }
            }
            _ => {}
        }
    }

    if depth == 0 {
        input.strip_prefix('(')?.strip_suffix(')')
    } else {
        None
    }
}

fn split_constructor_pattern(input: &str) -> Option<(&str, Vec<String>)> {
    let mut depth = 0usize;
    let mut start = None;

    for (idx, ch) in input.char_indices() {
        match ch {
            '(' => {
                if depth == 0 {
                    start = Some(idx);
                }
                depth += 1;
            }
            ')' => {
                depth = depth.checked_sub(1)?;
                if depth == 0 && idx != input.len() - 1 {
                    return None;
                }
            }
            _ => {}
        }
    }

    if depth != 0 {
        return None;
    }

    let start = start?;
    let constructor = input[..start].trim();
    if constructor.is_empty() {
        return None;
    }

    let inner = input[start + 1..input.len() - 1].trim();
    Some((constructor, split_top_level_commas(inner)))
}

fn split_top_level_commas(input: &str) -> Vec<String> {
    let mut parts = Vec::new();
    let mut start = 0usize;
    let mut paren_depth = 0usize;
    let mut bracket_depth = 0usize;
    let mut brace_depth = 0usize;

    for (idx, ch) in input.char_indices() {
        match ch {
            '(' => paren_depth += 1,
            ')' => paren_depth = paren_depth.saturating_sub(1),
            '[' => bracket_depth += 1,
            ']' => bracket_depth = bracket_depth.saturating_sub(1),
            '{' => brace_depth += 1,
            '}' => brace_depth = brace_depth.saturating_sub(1),
            ',' if paren_depth == 0 && bracket_depth == 0 && brace_depth == 0 => {
                parts.push(input[start..idx].trim().to_string());
                start = idx + ch.len_utf8();
            }
            _ => {}
        }
    }

    let last = input[start..].trim();
    if !last.is_empty() {
        parts.push(last.to_string());
    }

    parts
}

/// Structural match of a formal type against an actual type.
/// Entries in `generic_names` (the callee's type parameters) act as unification
/// variables; all other names are treated as concrete identifiers that must match
/// literally.  Writes the recovered substitution into `subst`.
fn unify_type(
    formal: &Type,
    actual: &Type,
    generic_names: &HashSet<String>,
    subst: &mut HashMap<String, Type>,
) -> bool {
    match formal {
        Type::Named(name) if generic_names.contains(name) => match subst.get(name) {
            Some(existing) => types_equal(existing, actual),
            None => {
                subst.insert(name.clone(), actual.clone());
                true
            }
        },
        Type::Named(name) => matches!(actual, Type::Named(n) if n == name),
        Type::Generic(name, params) => match actual {
            Type::Generic(aname, aparams) if name == aname && params.len() == aparams.len() => {
                params
                    .iter()
                    .zip(aparams)
                    .all(|(f, a)| unify_type(f, a, generic_names, subst))
            }
            _ => false,
        },
        Type::Tuple(ftypes) => match actual {
            Type::Tuple(atypes) if ftypes.len() == atypes.len() => ftypes
                .iter()
                .zip(atypes)
                .all(|(f, a)| unify_type(f, a, generic_names, subst)),
            _ => false,
        },
        Type::Unit => matches!(actual, Type::Unit),
        Type::Never => matches!(actual, Type::Never),
        _ => types_equal(formal, actual),
    }
}

fn types_equal(a: &Type, b: &Type) -> bool {
    match (a, b) {
        (Type::Named(n1), Type::Named(n2)) => n1 == n2,
        (Type::Generic(n1, p1), Type::Generic(n2, p2)) => {
            n1 == n2 && p1.len() == p2.len() && p1.iter().zip(p2).all(|(x, y)| types_equal(x, y))
        }
        (Type::Tuple(t1), Type::Tuple(t2)) => {
            t1.len() == t2.len() && t1.iter().zip(t2).all(|(x, y)| types_equal(x, y))
        }
        (Type::Path(p1), Type::Path(p2)) => p1 == p2,
        (Type::Reference(t1, r1, m1), Type::Reference(t2, r2, m2)) => {
            r1 == r2 && m1 == m2 && types_equal(t1, t2)
        }
        (Type::CallableTrait(c1), Type::CallableTrait(c2)) => {
            std::mem::discriminant(&c1.qualifier) == std::mem::discriminant(&c2.qualifier)
                && c1.trait_name == c2.trait_name
                && c1.args.len() == c2.args.len()
                && c1.args.iter().zip(&c2.args).all(|(x, y)| types_equal(x, y))
                && types_equal(&c1.return_type, &c2.return_type)
        }
        (Type::Slice(t1), Type::Slice(t2)) => types_equal(t1, t2),
        (Type::Array(t1, n1), Type::Array(t2, n2)) => n1 == n2 && types_equal(t1, t2),
        (Type::Unit, Type::Unit) | (Type::Never, Type::Never) => true,
        _ => false,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parse_rust_source;

    fn optimize_and_print(source: &str) -> String {
        optimize_and_print_with_options(source, CopyOptions::default())
    }

    fn optimize_and_print_with_options(source: &str, options: CopyOptions) -> String {
        let mut module = parse_rust_source(source, "Test").expect("parse source");
        optimize_copy_with_options(&mut module, options);
        let mut generator = RustCodeGenerator::new();
        generator.generate_module_code(&module)
    }

    #[test]
    fn prunes_unused_copy_specializations_by_default() {
        let source = r#"
pub fn dup<A>(x: A) -> (A, A)
where
    A: Clone + 'static
{
    (x.clone(), x.clone())
}
"#;

        let printed = optimize_and_print(source);
        assert!(!printed.contains("pub fn dup_copy"));
        assert!(!printed.contains("Copy-specialized bounds"));
    }

    #[test]
    fn keep_unused_copy_option_preserves_copy_specializations() {
        let source = r#"
pub fn dup<A>(x: A) -> (A, A)
where
    A: Clone + 'static
{
    (x.clone(), x.clone())
}
"#;

        let printed = optimize_and_print_with_options(
            source,
            CopyOptions {
                keep_unused_copy: true,
            },
        );
        assert!(printed.contains("pub fn dup_copy"));
        assert!(printed.contains("Copy-specialized bounds"));
    }

    #[test]
    fn keeps_copy_specializations_reachable_from_copy_call() {
        let source = r#"
pub fn dup<A>(x: A) -> (A, A)
where
    A: Clone + 'static
{
    (x.clone(), x.clone())
}

pub fn use_dup(x: bool) -> (bool, bool) {
    dup(x)
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("pub fn dup_copy"));
        assert!(printed.contains("dup_copy(x)"));
    }

    #[test]
    fn copy_call_checks_only_generics_upgraded_by_the_specialization() {
        let source = r#"
pub fn duplicate_first<A, B>(x: A, other: B) -> ((A, A), B)
where
    A: Clone + 'static,
    B: Clone + 'static
{
    ((x.clone(), x.clone()), other)
}

pub fn use_duplicate_first(x: bool, other: String) -> ((bool, bool), String) {
    duplicate_first(x, other)
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("pub fn duplicate_first_copy"));
        assert!(printed.contains("duplicate_first_copy(x, other)"));
    }

    #[test]
    fn removes_copy_clone_inside_deref_callee() {
        let source = r#"
use std::rc::Rc;

pub fn partial_triple(x: bool) -> Rc<dyn Fn(bool, bool) -> (bool, (bool, bool))> {
    Rc::new(move |a : bool, b : bool| {
        (x, (a, b))
    })
}

pub fn call_partial_triple(x: bool, y: bool) -> (bool, (bool, bool)) {
    (*partial_triple(x.clone()))(y, x)
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("(*partial_triple(x))(y, x)"));
        assert!(!printed.contains("partial_triple(x.clone())"));
    }

    #[test]
    fn package_copy_inference_rewrites_imported_pattern_payloads() {
        let mut string_module = parse_rust_source(
            r#"
#[derive(Clone)]
pub enum Char {
    Char(bool)
}
"#,
            "String",
        )
        .expect("parse String module");
        let mut list_module = parse_rust_source(
            r#"
#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons(A, Box<List<A>>)
}
"#,
            "List",
        )
        .expect("parse List module");
        let mut consumer_module = parse_rust_source(
            r#"
use crate::List::List;
use crate::String::Char;

pub fn first_two(x0: List<Char>) -> (Char, Char) {
    match x0 {
        List::Cons(x, rest) => match *rest {
            List::Cons(y, _) => (x.clone(), y.clone()),
            _ => panic!("short list"),
        },
        _ => panic!("short list"),
    }
}
"#,
            "Consumer",
        )
        .expect("parse consumer module");

        {
            let mut modules = vec![
                (
                    vec!["crate".to_string(), "String".to_string()],
                    &mut string_module,
                ),
                (
                    vec!["crate".to_string(), "List".to_string()],
                    &mut list_module,
                ),
                (
                    vec!["crate".to_string(), "Consumer".to_string()],
                    &mut consumer_module,
                ),
            ];
            let analysis = optimize_copy_modules_with_paths(&mut modules, CopyOptions::default());
            assert!(analysis.copy_types.contains("Char"));
        }

        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&consumer_module);
        assert!(printed.contains("(x, y)"));
        assert!(!printed.contains("x.clone()"));
        assert!(!printed.contains("y.clone()"));
    }

    #[test]
    fn package_copy_inference_redirects_imported_copy_specializations() {
        let mut callee_module = parse_rust_source(
            r#"
pub fn duplicate<A>(x: A) -> (A, A)
where
    A: Clone + 'static
{
    (x.clone(), x.clone())
}
"#,
            "Callee",
        )
        .expect("parse callee module");
        let mut caller_module = parse_rust_source(
            r#"
use crate::Callee::duplicate;

pub fn use_duplicate(x: bool) -> (bool, bool) {
    duplicate(x)
}
"#,
            "Caller",
        )
        .expect("parse caller module");

        {
            let mut modules = vec![
                (
                    vec!["crate".to_string(), "Callee".to_string()],
                    &mut callee_module,
                ),
                (
                    vec!["crate".to_string(), "Caller".to_string()],
                    &mut caller_module,
                ),
            ];
            optimize_copy_modules_with_paths(&mut modules, CopyOptions::default());
        }

        let mut generator = RustCodeGenerator::new();
        let callee = generator.generate_module_code(&callee_module);
        let caller = generator.generate_module_code(&caller_module);
        assert!(callee.contains("pub fn duplicate_copy"));
        assert!(caller.contains("crate::Callee::duplicate_copy(x)"));
    }

    #[test]
    fn package_copy_inference_keeps_same_named_types_scoped() {
        let mut copy_module = parse_rust_source(
            r#"
#[derive(Clone)]
pub struct Token(pub bool);
"#,
            "CopyDef",
        )
        .expect("parse CopyDef module");
        let mut owned_module = parse_rust_source(
            r#"
#[derive(Clone)]
pub struct Token(pub Box<bool>);
"#,
            "OwnedDef",
        )
        .expect("parse OwnedDef module");
        let mut consumer_module = parse_rust_source(
            r#"
use crate::CopyDef::Token;

pub fn duplicate(x: Token) -> (Token, Token) {
    (x.clone(), x)
}
"#,
            "Consumer",
        )
        .expect("parse consumer module");

        let analysis = {
            let mut modules = vec![
                (
                    vec!["crate".to_string(), "CopyDef".to_string()],
                    &mut copy_module,
                ),
                (
                    vec!["crate".to_string(), "OwnedDef".to_string()],
                    &mut owned_module,
                ),
                (
                    vec!["crate".to_string(), "Consumer".to_string()],
                    &mut consumer_module,
                ),
            ];
            optimize_copy_modules_with_paths(&mut modules, CopyOptions::default())
        };

        let mut generator = RustCodeGenerator::new();
        let copy_def = generator.generate_module_code(&copy_module);
        let owned_def = generator.generate_module_code(&owned_module);
        let consumer = generator.generate_module_code(&consumer_module);
        assert!(copy_def.contains("#[derive(Clone, Copy)]"));
        assert!(!owned_def.contains("#[derive(Clone, Copy)]"));
        assert!(consumer.contains("(x, x)"));
        assert!(!consumer.contains("x.clone()"));
        // Borrow receives simple names, so an ambiguous leaf name is exposed
        // only when every package definition with that name is Copy.
        assert!(!analysis.copy_types.contains("Token"));
    }
}
