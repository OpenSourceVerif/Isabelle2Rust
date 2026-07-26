use std::collections::{HashMap, HashSet};

use rustlightast::*;

use crate::rustlight_parser::TYPE_FACT_ONLY_DOC;

/// Result of the copy-analysis pass.
#[derive(Debug, Clone, Default)]
pub struct CopyAnalysis {
    /// Simple type names whose `Copy` implementation was inferred and
    /// materialized by this pass. Pre-existing source `Copy` facts and Rust
    /// primitives are deliberately excluded so downstream ablations can turn
    /// off only the facts contributed by Copy inference.
    pub inferred_copy_types: HashSet<String>,
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

#[derive(Debug, Clone)]
struct ExplicitCopyImpl {
    target: Type,
    generic_names: HashSet<String>,
    copy_generics: HashSet<String>,
    scope: ModuleScope,
}

struct CopyContext {
    copy_types: HashSet<ItemId>,
    /// Copy facts present before the inference fixed point starts: Rust
    /// primitives and source types already carrying `#[derive(Copy)]`.
    source_copy_types: HashSet<ItemId>,
    explicit_copy_impls: Vec<ExplicitCopyImpl>,
    type_defs: HashMap<ItemId, TypeDef>,
    type_aliases: HashMap<ItemId, (Vec<String>, Type, ModuleScope)>,
    variant_owners: HashMap<ItemId, Option<ItemId>>,
    functions: HashMap<ItemId, Type>,
    // Full signatures for C-Call: generic params + parameter types
    fn_sigs: HashMap<ItemId, (Vec<GenericParam>, Vec<Type>)>,
    function_defs: HashMap<ItemId, (FunctionDef, ModuleScope)>,
    copy_upgrade_requirements: HashMap<ItemId, HashSet<String>>,
    copy_specializations: HashMap<ItemId, CopySpecialization>,
    generated_copy_specializations: HashSet<ItemId>,
}

/// Infer Copy data types for the Rust fragment generated from Isabelle/HOL,
/// add Copy derives, and remove redundant `.clone()` calls whose receiver has
/// a statically known Copy type.
///
/// This pass intentionally stays on the paper's copy-inference side of the
/// pipeline: it does not optimize borrow/reference expressions, which belong
/// to later optimization stages.
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
    ctx.infer_copy_specialization_requirements();

    for (module_path, module) in modules.iter_mut() {
        ctx.apply_copy_derives(&mut module.items, module_path);
    }
    for (module_path, module) in modules.iter_mut() {
        ctx.add_copy_specializations(&mut module.items, module_path);
    }
    for (module_path, module) in modules.iter_mut() {
        ctx.rewrite_items(&mut module.items, module_path);
    }
    ctx.retain_effective_copy_specializations_in_modules(modules);
    ctx.finalize_copy_specialization_modes(modules, options.keep_unused_copy);

    CopyAnalysis {
        inferred_copy_types: ctx.public_inferred_copy_type_names(),
    }
}

impl CopyContext {
    fn from_modules(modules: &[(Vec<String>, &mut RustModule)]) -> Self {
        let mut ctx = Self {
            copy_types: primitive_copy_types()
                .into_iter()
                .map(|name| vec![name.to_string()])
                .collect(),
            source_copy_types: HashSet::new(),
            explicit_copy_impls: Vec::new(),
            type_defs: HashMap::new(),
            type_aliases: HashMap::new(),
            variant_owners: HashMap::new(),
            functions: HashMap::new(),
            fn_sigs: HashMap::new(),
            function_defs: HashMap::new(),
            copy_upgrade_requirements: HashMap::new(),
            copy_specializations: HashMap::new(),
            generated_copy_specializations: HashSet::new(),
        };

        for (module_path, module) in modules {
            ctx.collect_items(&module.items, module_path);
        }
        ctx.source_copy_types = ctx.copy_types.clone();

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
                if def.derives.iter().any(|derive| derive == "Copy") {
                    self.copy_types.insert(id.clone());
                }
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
                if def.derives.iter().any(|derive| derive == "Copy") {
                    self.copy_types.insert(owner_id.clone());
                }
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
                    (
                        alias
                            .generics
                            .iter()
                            .map(|generic| generic.name.clone())
                            .collect(),
                        alias.target.clone(),
                        scope.clone(),
                    ),
                );
            }
            Item::Function(function) => {
                let id = item_id(scope, &function.name);
                self.functions
                    .insert(id.clone(), function.return_type.clone());
                self.fn_sigs.insert(
                    id.clone(),
                    (
                        function.generics.clone(),
                        function.params.iter().map(|p| p.ty.clone()).collect(),
                    ),
                );
                if !function.docs.iter().any(|doc| doc == TYPE_FACT_ONLY_DOC) {
                    self.function_defs
                        .insert(id, (function.clone(), scope.clone()));
                }
            }
            Item::Impl(impl_block)
                if impl_block
                    .trait_impl
                    .as_ref()
                    .is_some_and(type_is_copy_trait) =>
            {
                let generic_names = impl_block
                    .generics
                    .iter()
                    .map(|generic| generic.name.clone())
                    .collect::<HashSet<_>>();
                let copy_generics = generic_param_names_with_bound(&impl_block.generics, "Copy");
                self.explicit_copy_impls.push(ExplicitCopyImpl {
                    target: impl_block.target.clone(),
                    generic_names,
                    copy_generics,
                    scope: scope.clone(),
                });
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

            for (name, (_, target, scope)) in &self.type_aliases {
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

    fn infer_copy_specialization_requirements(&mut self) {
        let functions = self
            .function_defs
            .iter()
            .map(|(id, (function, scope))| (id.clone(), function.clone(), scope.clone()))
            .collect::<Vec<_>>();
        let mut requirements = HashMap::<ItemId, HashSet<String>>::new();

        loop {
            let previous = requirements.clone();
            let mut changed = false;

            for (id, function, scope) in &functions {
                let clone_generics = function
                    .generics
                    .iter()
                    .filter(|generic| has_bound(generic, "Clone") && !has_bound(generic, "Copy"))
                    .map(|generic| generic.name.clone())
                    .collect::<HashSet<_>>();
                if clone_generics.is_empty() {
                    continue;
                }

                let env = function_type_env(function);
                let copy_generics = generic_names_with_bound(function, "Copy");
                let mut inferred = previous.get(id).cloned().unwrap_or_default();
                self.collect_copy_bound_candidates(
                    &function.body,
                    &env,
                    scope,
                    &clone_generics,
                    &copy_generics,
                    Some(&previous),
                    &mut inferred,
                );
                inferred.retain(|generic| clone_generics.contains(generic));

                if previous.get(id) != Some(&inferred) && !inferred.is_empty() {
                    changed = true;
                }
                if !inferred.is_empty() {
                    requirements.insert(id.clone(), inferred);
                }
            }

            if !changed {
                break;
            }
        }

        self.copy_upgrade_requirements = requirements;
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
        if self.explicit_copy_impl_applies(ty, scope, copy_generics) {
            return true;
        }

        match ty {
            Type::Named(name) => {
                copy_generics.contains(name)
                    || self.copy_types.contains(&scope.resolve_name_path(name))
            }
            Type::Path(path) => self.copy_types.contains(&scope.resolve_segments(path)),
            Type::Generic(name, params) => {
                if type_name_leaf(name) == "PhantomData" {
                    true
                } else {
                    self.copy_types
                        .contains(&resolve_type_constructor_name(name, scope))
                        && params
                            .iter()
                            .all(|param| self.type_is_copy_in_scope(param, scope, copy_generics))
                }
            }
            Type::Tuple(types) => types
                .iter()
                .all(|ty| self.type_is_copy_in_scope(ty, scope, copy_generics)),
            Type::Array(inner, _) => self.type_is_copy_in_scope(inner, scope, copy_generics),
            Type::Unit | Type::Never => true,
            // Rust shared references are `Copy`; mutable references are not.
            Type::Reference(_, true, false) => true,
            Type::Reference(_, _, _) => false,
            Type::CallableTrait(_) => false,
            Type::Slice(_) => false,
        }
    }

    fn explicit_copy_impl_applies(
        &self,
        ty: &Type,
        scope: &ModuleScope,
        copy_generics: &HashSet<String>,
    ) -> bool {
        let Some(actual_id) = type_constructor_id(ty, scope) else {
            return false;
        };
        let Some(actual_name) = type_leaf_name(ty) else {
            return false;
        };
        let matching_ids = self
            .explicit_copy_impls
            .iter()
            .filter(|rule| type_leaf_name(&rule.target) == Some(actual_name))
            .filter_map(|rule| type_constructor_id(&rule.target, &rule.scope))
            .collect::<HashSet<_>>();
        let unique_leaf_match = matching_ids.len() == 1;

        self.explicit_copy_impls.iter().any(|rule| {
            let rule_id = type_constructor_id(&rule.target, &rule.scope);
            let exact_match = rule_id.as_ref() == Some(&actual_id);
            let unambiguous_leaf_match =
                unique_leaf_match && type_leaf_name(&rule.target) == Some(actual_name);
            if !exact_match && !unambiguous_leaf_match {
                return false;
            }

            let mut subst = HashMap::new();
            if !unify_type(&rule.target, ty, &rule.generic_names, &mut subst) {
                return false;
            }

            rule.copy_generics.iter().all(|generic| {
                subst
                    .get(generic)
                    .is_some_and(|actual| self.type_is_copy_in_scope(actual, scope, copy_generics))
            })
        })
    }

    fn public_inferred_copy_type_names(&self) -> HashSet<String> {
        let mut definitions_by_name: HashMap<&str, Vec<&ItemId>> = HashMap::new();
        for id in self.type_defs.keys().chain(self.type_aliases.keys()) {
            if let Some(name) = id.last() {
                definitions_by_name.entry(name).or_default().push(id);
            }
        }

        let mut names = HashSet::new();
        for (name, ids) in definitions_by_name {
            if ids.iter().all(|id| self.copy_types.contains(*id))
                && ids.iter().any(|id| !self.source_copy_types.contains(*id))
            {
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
                Item::Struct(def)
                    if self.copy_types.contains(&item_id(&scope, &def.name))
                        && !self.has_explicit_copy_impl(&item_id(&scope, &def.name)) =>
                {
                    ensure_item_comment(&mut def.docs, "// copy-optimized by inferred Copy derive");
                    ensure_clone_copy_derives(&mut def.derives);
                }
                Item::Enum(def)
                    if self.copy_types.contains(&item_id(&scope, &def.name))
                        && !self.has_explicit_copy_impl(&item_id(&scope, &def.name)) =>
                {
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

    fn has_explicit_copy_impl(&self, id: &ItemId) -> bool {
        self.explicit_copy_impls
            .iter()
            .any(|rule| type_constructor_id(&rule.target, &rule.scope).as_ref() == Some(id))
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
                        &original_id,
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

    /// Discard a candidate unless strengthening its bounds has an observable
    /// effect in the generated program.  A leaf specialization must either
    /// remove a clone or preserve a Copy-sensitive match clone for the Borrow
    /// pass.  Wrapper specializations are retained only when their rewritten
    /// body actually calls another effective specialization.
    fn retain_effective_copy_specializations_in_modules(
        &mut self,
        modules: &mut [(Vec<String>, &mut RustModule)],
    ) {
        if self.copy_specializations.is_empty() {
            return;
        }

        let functions = collect_located_functions(modules);
        let generated = self.generated_copy_specializations.clone();
        let mut direct_effects = HashSet::new();
        let mut specialization_calls = HashMap::<ItemId, HashSet<ItemId>>::new();

        for (original_id, specialization) in &self.copy_specializations {
            let Some((original, original_scope)) = functions.get(original_id) else {
                continue;
            };
            let Some((specialized, specialized_scope)) = functions.get(&specialization.id) else {
                continue;
            };

            let original_clones = count_clone_calls_in_block(&original.body);
            let specialized_clones = count_clone_calls_in_block(&specialized.body);
            if specialized_clones < original_clones
                || self.specialization_preserves_borrow_effect(
                    original_id,
                    original,
                    original_scope,
                    specialized_clones,
                )
            {
                direct_effects.insert(specialization.id.clone());
            }

            let mut calls = HashSet::new();
            collect_generated_calls_block(
                &specialized.body,
                specialized_scope,
                &generated,
                &mut calls,
            );
            specialization_calls.insert(specialization.id.clone(), calls);
        }

        let mut effective = direct_effects;
        loop {
            let mut changed = false;
            for (specialization, calls) in &specialization_calls {
                if !effective.contains(specialization)
                    && calls.iter().any(|callee| effective.contains(callee))
                {
                    effective.insert(specialization.clone());
                    changed = true;
                }
            }
            if !changed {
                break;
            }
        }

        let invalid = self
            .copy_specializations
            .iter()
            .filter_map(|(original, specialization)| {
                (!effective.contains(&specialization.id))
                    .then(|| (original.clone(), specialization.id.clone()))
            })
            .collect::<Vec<_>>();
        if !invalid.is_empty() {
            self.apply_specialization_decisions(modules, &HashSet::new(), &invalid);
        }
    }

    fn specialization_preserves_borrow_effect(
        &self,
        function_id: &ItemId,
        function: &FunctionDef,
        scope: &ModuleScope,
        remaining_clones: usize,
    ) -> bool {
        if remaining_clones == 0 {
            return false;
        }

        let clone_generics = function
            .generics
            .iter()
            .filter(|generic| has_bound(generic, "Clone") && !has_bound(generic, "Copy"))
            .map(|generic| generic.name.clone())
            .collect::<HashSet<_>>();
        let Some(upgraded) = self.copy_upgrade_requirements.get(function_id) else {
            return false;
        };
        if clone_generics.is_empty() || upgraded.is_empty() {
            return false;
        }

        // Recompute direct demands without transitive callee requirements.  If
        // a tracked clone remains after Copy rewriting, it is the match clone
        // deliberately preserved for B-Match rather than an inert wrapper.
        let mut direct = HashSet::new();
        self.collect_copy_bound_candidates(
            &function.body,
            &function_type_env(function),
            scope,
            &clone_generics,
            &generic_names_with_bound(function, "Copy"),
            None,
            &mut direct,
        );
        direct.retain(|generic| upgraded.contains(generic));
        !direct.is_empty()
    }

    /// Classify each effective candidate by reachability.  If only its Copy
    /// node is reachable, fold that body back into the original function and
    /// strengthen the original bounds.  If both nodes are reachable, retain
    /// the `_copy` specialization.  An unreachable Copy node is removed unless
    /// the diagnostic `keep_unused_copy` option was requested.
    fn finalize_copy_specialization_modes(
        &mut self,
        modules: &mut [(Vec<String>, &mut RustModule)],
        keep_unused_copy: bool,
    ) {
        if self.copy_specializations.is_empty() {
            return;
        }

        let functions = collect_located_functions(modules);
        let mut targets = HashSet::new();
        for (original, specialization) in &self.copy_specializations {
            targets.insert(original.clone());
            targets.insert(specialization.id.clone());
        }

        let mut edges = HashMap::<ItemId, HashSet<ItemId>>::new();
        let mut roots = HashSet::new();
        for (id, (function, scope)) in &functions {
            let mut calls = HashSet::new();
            collect_generated_calls_block(&function.body, scope, &targets, &mut calls);
            if targets.contains(id) {
                edges.insert(id.clone(), calls);
            } else {
                roots.extend(calls);
            }
        }
        for (module_path, module) in modules.iter() {
            collect_non_function_target_calls(&module.items, module_path, &targets, &mut roots);
        }

        let mut reachable = HashSet::new();
        let mut worklist = roots.into_iter().collect::<Vec<_>>();
        while let Some(id) = worklist.pop() {
            if reachable.insert(id.clone()) {
                if let Some(calls) = edges.get(&id) {
                    worklist.extend(calls.iter().cloned());
                }
            }
        }

        // A candidate whose Copy node has no reachable caller keeps its
        // Clone-constrained original.  Calls made by that surviving original
        // must therefore participate in reachability too; otherwise a callee
        // can be folded to Copy while the retained caller still supplies only
        // Clone (for example, a generic wrapper around another candidate).
        let retained_originals = self
            .copy_specializations
            .iter()
            .filter_map(|(original, specialization)| {
                (!reachable.contains(&specialization.id)).then(|| original.clone())
            })
            .collect::<Vec<_>>();
        worklist.extend(retained_originals);
        while let Some(id) = worklist.pop() {
            if reachable.insert(id.clone()) {
                if let Some(calls) = edges.get(&id) {
                    worklist.extend(calls.iter().cloned());
                }
            }
        }

        let mut fold = HashSet::new();
        let mut remove = Vec::new();
        for (original, specialization) in &self.copy_specializations {
            let original_reachable = reachable.contains(original);
            let copy_reachable = reachable.contains(&specialization.id);
            if copy_reachable && !original_reachable {
                fold.insert(original.clone());
                remove.push((original.clone(), specialization.id.clone()));
            } else if !copy_reachable && !keep_unused_copy {
                remove.push((original.clone(), specialization.id.clone()));
            }
        }

        if !remove.is_empty() {
            self.apply_specialization_decisions(modules, &fold, &remove);
        }
    }

    fn apply_specialization_decisions(
        &mut self,
        modules: &mut [(Vec<String>, &mut RustModule)],
        fold_originals: &HashSet<ItemId>,
        remove: &[(ItemId, ItemId)],
    ) {
        let replacements = remove
            .iter()
            .map(|(original, specialization)| (specialization.clone(), original.clone()))
            .collect::<HashMap<_, _>>();

        for (module_path, module) in modules.iter_mut() {
            rewrite_specialization_calls_in_items(&mut module.items, module_path, &replacements);
        }
        for (module_path, module) in modules.iter_mut() {
            apply_specialization_items(
                &mut module.items,
                module_path,
                fold_originals,
                &replacements,
            );
        }

        for (original, specialization) in remove {
            if fold_originals.contains(original) {
                if let Some((generics, params)) = self.fn_sigs.get(specialization).cloned() {
                    self.fn_sigs.insert(original.clone(), (generics, params));
                }
            }
            self.fn_sigs.remove(specialization);
            self.functions.remove(specialization);
            self.generated_copy_specializations.remove(specialization);
        }
        self.copy_specializations
            .retain(|original, _| !replacements.values().any(|removed| removed == original));
    }

    fn copy_specialization_for_function(
        &self,
        function_id: &ItemId,
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

        let copy_bound_candidates = self
            .copy_upgrade_requirements
            .get(function_id)
            .cloned()
            .unwrap_or_default();

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
            Item::Impl(impl_block) => {
                let impl_copy_generics =
                    generic_param_names_with_bound(&impl_block.generics, "Copy");
                for impl_item in &mut impl_block.items {
                    match impl_item {
                        ImplItem::Method(method) => self.rewrite_function_with_copy_generics(
                            method,
                            scope,
                            &impl_copy_generics,
                        ),
                        ImplItem::AssocConst(_, _, expr) => {
                            let mut env = TypeEnv::new();
                            self.rewrite_expr(expr, &mut env, scope, &impl_copy_generics);
                        }
                        ImplItem::AssocType(_, _) => {}
                    }
                }
            }
            Item::Mod(module) => {
                let mut nested_path = scope.module_path.clone();
                nested_path.push(module.name.clone());
                self.rewrite_items(&mut module.items, &nested_path);
            }
            _ => {}
        }
    }

    fn rewrite_function(&self, function: &mut FunctionDef, scope: &ModuleScope) {
        self.rewrite_function_with_copy_generics(function, scope, &HashSet::new());
    }

    fn rewrite_function_with_copy_generics(
        &self,
        function: &mut FunctionDef,
        scope: &ModuleScope,
        outer_copy_generics: &HashSet<String>,
    ) {
        let mut env = function_type_env(function);

        let mut copy_generics = generic_names_with_bound(function, "Copy");
        copy_generics.extend(outer_copy_generics.iter().cloned());

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
                        .is_some_and(|ty| {
                            !matches!(ty, Type::Reference(_, _, _))
                                && self.type_is_copy_in_scope(&ty, scope, copy_generics)
                        })
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
                // Preserve a top-level `x.clone()` until B-Match runs.  Its
                // presence records that the generated program copied the
                // outer object only to inspect it; erasing it here would make
                // the later Borrow pass mistake a large, non-consuming match
                // for an intentional move.  B-Match applies the size-aware
                // profitability rule and removes the clone in either the
                // by-value or by-reference form.
                let preserved_clone = match expr.as_mut() {
                    Expr::MethodCall(receiver, method, args)
                        if method == "clone" && args.is_empty() =>
                    {
                        self.rewrite_expr(receiver, env, scope, copy_generics);
                        true
                    }
                    _ => false,
                };
                if !preserved_clone {
                    self.rewrite_expr(expr, env, scope, copy_generics);
                }
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
                    let pattern = closure_param_pattern(param);
                    if let Some(ty) = closure_param_type(param) {
                        self.bind_pattern_types(&pattern, &ty, &mut closure_env, scope);
                    } else {
                        remove_pattern_types(&pattern, &mut closure_env);
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
        callee_requirements: Option<&HashMap<ItemId, HashSet<String>>>,
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
            callee_requirements,
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
        callee_requirements: Option<&HashMap<ItemId, HashSet<String>>>,
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
                            callee_requirements,
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
                    callee_requirements,
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
                callee_requirements,
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
        callee_requirements: Option<&HashMap<ItemId, HashSet<String>>>,
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
                        callee_requirements,
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
                    callee_requirements,
                    out,
                );
                for arg in args {
                    self.collect_clone_demands_expr(
                        arg,
                        env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        callee_requirements,
                        out,
                    );
                }

                if let Some(requirements) = callee_requirements {
                    self.collect_transitive_call_requirements(
                        callee,
                        args,
                        env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        requirements,
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
                    callee_requirements,
                    out,
                );
                for arg in args {
                    self.collect_clone_demands_expr(
                        arg,
                        env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        callee_requirements,
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
                    callee_requirements,
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
                    callee_requirements,
                    out,
                );
                self.collect_clone_demands(
                    then_branch,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    callee_requirements,
                    out,
                );
                if let Some(else_branch) = else_branch {
                    self.collect_clone_demands(
                        else_branch,
                        env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        callee_requirements,
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
                    callee_requirements,
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
                    callee_requirements,
                    out,
                );
                if let Some(else_branch) = else_branch {
                    self.collect_clone_demands(
                        else_branch,
                        env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        callee_requirements,
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
                    callee_requirements,
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
                            callee_requirements,
                            out,
                        );
                    }
                    self.collect_clone_demands(
                        &arm.body,
                        &arm_env,
                        scope,
                        tracked_generics,
                        required_copy_env,
                        callee_requirements,
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
                callee_requirements,
                out,
            ),
            Expr::BinaryOp(left, _, right) => {
                self.collect_clone_demands_expr(
                    left,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    callee_requirements,
                    out,
                );
                self.collect_clone_demands_expr(
                    right,
                    env,
                    scope,
                    tracked_generics,
                    required_copy_env,
                    callee_requirements,
                    out,
                );
            }
            Expr::UnaryOp(_, inner) => self.collect_clone_demands_expr(
                inner,
                env,
                scope,
                tracked_generics,
                required_copy_env,
                callee_requirements,
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

    fn collect_transitive_call_requirements(
        &self,
        callee: &Expr,
        args: &[Expr],
        env: &TypeEnv,
        scope: &ModuleScope,
        tracked_generics: &HashSet<String>,
        required_copy_env: Option<&HashSet<String>>,
        requirements: &HashMap<ItemId, HashSet<String>>,
        out: &mut HashSet<String>,
    ) {
        let Some(callee_id) = self.resolve_callee_id(callee, env, scope) else {
            return;
        };
        let Some(required_by_callee) = requirements.get(&callee_id) else {
            return;
        };
        let Some((generics, param_types)) = self.fn_sigs.get(&callee_id) else {
            return;
        };
        if args.len() != param_types.len() {
            return;
        }

        let callee_generics = generics
            .iter()
            .map(|generic| generic.name.clone())
            .collect::<HashSet<_>>();
        let mut subst = HashMap::new();
        for (formal, arg) in param_types.iter().zip(args) {
            if let Some(actual) = self.infer_expr_type(arg, env, scope) {
                if !unify_type(formal, &actual, &callee_generics, &mut subst) {
                    return;
                }
            }
        }

        for required in required_by_callee {
            let Some(actual) = subst.get(required) else {
                continue;
            };
            let admissible = required_copy_env
                .map(|copy_env| self.type_is_copy_in_scope(actual, scope, copy_env))
                .unwrap_or(true);
            if !admissible {
                continue;
            }

            let mut caller_generics = HashSet::new();
            generic_names_in_type(actual, &mut caller_generics);
            caller_generics.retain(|name| tracked_generics.contains(name));
            out.extend(caller_generics);
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

        let mut subst = HashMap::new();
        for (formal, arg) in param_types.iter().zip(args) {
            if let Some(actual) = self.infer_expr_type(arg, env, scope) {
                if !unify_type(formal, &actual, &callee_generic_names, &mut subst) {
                    return None;
                }
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
            Expr::Call(callee, args) => self.infer_call_type(callee, args, env, scope),
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                self.infer_expr_type(receiver, env, scope)
            }
            Expr::Parenthesized(inner) => self.infer_expr_type(inner, env, scope),
            Expr::Cast(_, ty) => Some(ty.clone()),
            Expr::Block(block) => self.infer_block_type(block, env, scope),
            Expr::If {
                then_branch,
                else_branch: Some(else_branch),
                ..
            } => {
                let then_ty = self.expand_alias_type(
                    &self.infer_block_type(then_branch, env, scope)?,
                    scope,
                    &mut HashSet::new(),
                );
                let else_ty = self.expand_alias_type(
                    &self.infer_block_type(else_branch, env, scope)?,
                    scope,
                    &mut HashSet::new(),
                );
                self.types_equal_in_scope(&then_ty, &else_ty, scope)
                    .then_some(then_ty)
            }
            Expr::Match { arms, .. } => {
                let mut arm_types = arms
                    .iter()
                    .map(|arm| self.infer_block_type(&arm.body, env, scope));
                let first = arm_types.next()??;
                arm_types.try_fold(first, |expected, actual| {
                    let actual = actual?;
                    self.types_equal_in_scope(&expected, &actual, scope)
                        .then_some(expected)
                })
            }
            Expr::UnaryOp(op, inner) if op == "!" => {
                let inner_ty = self.infer_expr_type(inner, env, scope)?;
                matches!(inner_ty, Type::Named(ref name) if name == "bool")
                    .then(|| Type::Named("bool".to_string()))
            }
            Expr::UnaryOp(op, inner) if op == "*" => {
                match self.infer_expr_type(inner, env, scope)? {
                    Type::Generic(name, mut params)
                        if type_name_leaf(&name) == "Box" && params.len() == 1 =>
                    {
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

    fn infer_block_type(&self, block: &Block, env: &TypeEnv, scope: &ModuleScope) -> Option<Type> {
        let mut block_env = env.clone();

        for stmt in &block.stmts {
            if let Statement::Let(let_stmt) = stmt {
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
                } else {
                    remove_pattern_types(&let_stmt.name, &mut block_env);
                }
            }
        }

        block
            .expr
            .as_ref()
            .and_then(|expr| self.infer_expr_type(expr, &block_env, scope))
    }

    fn infer_call_type(
        &self,
        callee: &Expr,
        args: &[Expr],
        env: &TypeEnv,
        scope: &ModuleScope,
    ) -> Option<Type> {
        if let Some(ty) = explicit_identity_return_type(callee) {
            return Some(ty);
        }
        if let Some(ty) = explicit_qself_value_return_type(callee) {
            return Some(ty);
        }
        if let Some(ty) = self.infer_constructor_call_type(callee, args, env, scope) {
            return Some(ty);
        }

        let id = match callee {
            Expr::Ident(name) if env.contains_key(name) => return None,
            Expr::Ident(name) => scope.resolve_name_path(name),
            Expr::Path(path, PathType::Namespace) => scope.resolve_segments(path),
            Expr::Parenthesized(inner) => return self.infer_call_type(inner, args, env, scope),
            _ => return None,
        };
        let return_type = self.functions.get(&id)?.clone();
        let Some((generics, param_types)) = self.fn_sigs.get(&id) else {
            return Some(return_type);
        };
        let generic_names = generics
            .iter()
            .map(|generic| generic.name.clone())
            .collect::<HashSet<_>>();
        let mut subst = HashMap::new();
        for (formal, actual_expr) in param_types.iter().zip(args) {
            if let Some(actual) = self.infer_expr_type(actual_expr, env, scope) {
                let _ = unify_type(formal, &actual, &generic_names, &mut subst);
            }
        }
        Some(apply_type_subst(&return_type, &subst))
    }

    fn infer_constructor_call_type(
        &self,
        callee: &Expr,
        args: &[Expr],
        env: &TypeEnv,
        scope: &ModuleScope,
    ) -> Option<Type> {
        let (owner, variant_name) = match callee {
            Expr::Ident(name) => (
                self.owner_for_variant_name(name, scope)?,
                type_name_leaf(name).to_string(),
            ),
            Expr::Path(path, PathType::Namespace) => (
                self.owner_for_variant_path(path, scope)?,
                path.last().map(|name| type_name_leaf(name).to_string())?,
            ),
            Expr::Parenthesized(inner) => {
                return self.infer_constructor_call_type(inner, args, env, scope)
            }
            _ => return None,
        };
        let def = self.type_defs.get(&owner)?;
        let fields = match &def.kind {
            TypeDefKind::Enum(variants) => variants
                .iter()
                .find(|variant| variant.name == variant_name)?
                .fields
                .as_slice(),
            TypeDefKind::Struct(fields) => {
                if owner.last().is_none_or(|name| name != &variant_name) {
                    return None;
                }
                return self.instantiate_constructor_owner(
                    &owner,
                    def,
                    fields.iter().map(|f| &f.ty),
                    args,
                    env,
                    scope,
                );
            }
        };
        self.instantiate_constructor_owner(&owner, def, fields.iter(), args, env, scope)
    }

    fn instantiate_constructor_owner<'a>(
        &self,
        owner: &ItemId,
        def: &TypeDef,
        fields: impl Iterator<Item = &'a Type>,
        args: &[Expr],
        env: &TypeEnv,
        scope: &ModuleScope,
    ) -> Option<Type> {
        let generic_names = def.generics.iter().cloned().collect::<HashSet<_>>();
        let mut subst = HashMap::new();
        for (formal, actual_expr) in fields.zip(args) {
            let actual = self.infer_expr_type(actual_expr, env, scope)?;
            if !unify_type(formal, &actual, &generic_names, &mut subst) {
                return None;
            }
        }
        if def.generics.is_empty() {
            Some(Type::Path(owner.clone()))
        } else {
            let params = def
                .generics
                .iter()
                .map(|generic| subst.get(generic).cloned())
                .collect::<Option<Vec<_>>>()?;
            Some(Type::Generic(owner.join("::"), params))
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
                Type::Generic(name, params)
                    if type_name_leaf(name) == "Box" && params.len() == 1 =>
                {
                    &params[0]
                }
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

        let expanded_expected = self.expand_alias_type(expected, scope, &mut HashSet::new());

        if let Some(expected_id) = self.type_id_for_type(&expanded_expected, scope) {
            if let Some(def) = self.type_defs.get(&expected_id) {
                let subst = type_substitution(def, &expanded_expected);
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
        self.variant_owners
            .get(&variant_id)
            .cloned()
            .flatten()
            .or_else(|| {
                path.last()
                    .and_then(|variant| self.owner_for_variant_name(variant, scope))
            })
    }

    fn owner_for_variant_name(&self, variant_name: &str, scope: &ModuleScope) -> Option<ItemId> {
        let variant_id = scope.resolve_name_path(variant_name);
        if let Some(owner) = self.variant_owners.get(&variant_id).cloned().flatten() {
            return Some(owner);
        }

        let mut matches = self
            .variant_owners
            .iter()
            .filter(|(id, owner)| {
                owner.is_some()
                    && id.last().is_some_and(|name| name == variant_name)
                    && id.starts_with(&scope.module_path)
            })
            .filter_map(|(_, owner)| owner.clone());
        let first = matches.next()?;
        matches.all(|owner| owner == first).then_some(first)
    }

    fn type_id_for_type(&self, ty: &Type, scope: &ModuleScope) -> Option<ItemId> {
        let direct = match ty {
            Type::Named(name) => Some(scope.resolve_name_path(name)),
            Type::Generic(name, _) => Some(resolve_type_constructor_name(name, scope)),
            Type::Path(path) => Some(scope.resolve_segments(path)),
            Type::Reference(inner, _, _) => self.type_id_for_type(inner, scope),
            _ => None,
        }?;
        if let Some((_, target, alias_scope)) = self.type_aliases.get(&direct) {
            self.type_id_for_type(target, alias_scope)
        } else {
            Some(direct)
        }
    }

    fn expand_alias_type(
        &self,
        ty: &Type,
        scope: &ModuleScope,
        visiting: &mut HashSet<ItemId>,
    ) -> Type {
        let id = match ty {
            Type::Named(name) => scope.resolve_name_path(name),
            Type::Generic(name, _) => resolve_type_constructor_name(name, scope),
            Type::Path(path) => scope.resolve_segments(path),
            _ => return ty.clone(),
        };
        if !visiting.insert(id.clone()) {
            return ty.clone();
        }
        let Some((generics, target, alias_scope)) = self.type_aliases.get(&id) else {
            return ty.clone();
        };
        let subst = match ty {
            Type::Generic(_, params) if params.len() == generics.len() => generics
                .iter()
                .cloned()
                .zip(params.iter().cloned())
                .collect(),
            _ => HashMap::new(),
        };
        let expanded = apply_type_subst(target, &subst);
        self.expand_alias_type(&expanded, alias_scope, visiting)
    }

    fn types_equal_in_scope(&self, left: &Type, right: &Type, scope: &ModuleScope) -> bool {
        let left = self.expand_alias_type(left, scope, &mut HashSet::new());
        let right = self.expand_alias_type(right, scope, &mut HashSet::new());
        match (&left, &right) {
            (Type::Named(a), Type::Named(b)) => {
                scope.resolve_name_path(a) == scope.resolve_name_path(b)
            }
            (Type::Named(a), Type::Path(b)) | (Type::Path(b), Type::Named(a)) => {
                scope.resolve_name_path(a) == scope.resolve_segments(b)
            }
            (Type::Path(a), Type::Path(b)) => {
                scope.resolve_segments(a) == scope.resolve_segments(b)
            }
            (Type::Generic(a, ap), Type::Generic(b, bp)) => {
                ap.len() == bp.len()
                    && resolve_type_constructor_name(a, scope)
                        == resolve_type_constructor_name(b, scope)
                    && ap
                        .iter()
                        .zip(bp)
                        .all(|(a, b)| self.types_equal_in_scope(a, b, scope))
            }
            (Type::Tuple(a), Type::Tuple(b)) => {
                a.len() == b.len()
                    && a.iter()
                        .zip(b)
                        .all(|(a, b)| self.types_equal_in_scope(a, b, scope))
            }
            (Type::Array(a, an), Type::Array(b, bn)) => {
                an == bn && self.types_equal_in_scope(a, b, scope)
            }
            (Type::Reference(a, ar, am), Type::Reference(b, br, bm)) => {
                ar == br && am == bm && self.types_equal_in_scope(a, b, scope)
            }
            _ => types_equal(&left, &right),
        }
    }
}

fn collect_located_functions(
    modules: &[(Vec<String>, &mut RustModule)],
) -> HashMap<ItemId, (FunctionDef, ModuleScope)> {
    let mut functions = HashMap::new();
    for (module_path, module) in modules {
        collect_located_functions_in_items(&module.items, module_path, &mut functions);
    }
    functions
}

fn collect_located_functions_in_items(
    items: &[Item],
    module_path: &[String],
    out: &mut HashMap<ItemId, (FunctionDef, ModuleScope)>,
) {
    let scope = ModuleScope {
        module_path: module_path.to_vec(),
        imports: collect_imports(items),
    };
    for item in items {
        match item {
            Item::Function(function) => {
                out.insert(
                    item_id(&scope, &function.name),
                    (function.clone(), scope.clone()),
                );
            }
            Item::Mod(module) => {
                let mut nested_path = module_path.to_vec();
                nested_path.push(module.name.clone());
                collect_located_functions_in_items(&module.items, &nested_path, out);
            }
            _ => {}
        }
    }
}

fn collect_non_function_target_calls(
    items: &[Item],
    module_path: &[String],
    targets: &HashSet<ItemId>,
    out: &mut HashSet<ItemId>,
) {
    let scope = ModuleScope {
        module_path: module_path.to_vec(),
        imports: collect_imports(items),
    };
    for item in items {
        match item {
            Item::Function(_) => {}
            Item::Impl(_) | Item::Const(_) | Item::LazyStatic(_) => {
                collect_generated_calls_item(item, &scope, targets, out);
            }
            Item::Mod(module) => {
                let mut nested_path = module_path.to_vec();
                nested_path.push(module.name.clone());
                collect_non_function_target_calls(&module.items, &nested_path, targets, out);
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

fn apply_specialization_items(
    items: &mut Vec<Item>,
    module_path: &[String],
    fold_originals: &HashSet<ItemId>,
    replacements: &HashMap<ItemId, ItemId>,
) {
    let scope = ModuleScope {
        module_path: module_path.to_vec(),
        imports: collect_imports(items),
    };
    let specialized_functions = items
        .iter()
        .filter_map(|item| {
            let Item::Function(function) = item else {
                return None;
            };
            Some((item_id(&scope, &function.name), function.clone()))
        })
        .collect::<HashMap<_, _>>();

    for item in &mut *items {
        match item {
            Item::Function(function) => {
                let original_id = item_id(&scope, &function.name);
                if fold_originals.contains(&original_id) {
                    let specialization_id =
                        replacements.iter().find_map(|(specialization, original)| {
                            (original == &original_id).then_some(specialization)
                        });
                    if let Some(mut specialized) = specialization_id
                        .and_then(|id| specialized_functions.get(id))
                        .cloned()
                    {
                        specialized.name = function.name.clone();
                        specialized.docs.retain(|doc| {
                            doc.trim() != "// copy-optimized by Copy-specialized bounds"
                        });
                        ensure_function_comment(
                            &mut specialized,
                            "// copy-optimized by globally tightened Copy bounds",
                        );
                        *function = specialized;
                    }
                }
            }
            Item::Mod(module) => {
                let mut nested_path = module_path.to_vec();
                nested_path.push(module.name.clone());
                apply_specialization_items(
                    &mut module.items,
                    &nested_path,
                    fold_originals,
                    replacements,
                );
            }
            _ => {}
        }
    }

    items.retain(|item| {
        let Item::Function(function) = item else {
            return true;
        };
        !replacements.contains_key(&item_id(&scope, &function.name))
    });
}

fn rewrite_specialization_calls_in_items(
    items: &mut [Item],
    module_path: &[String],
    replacements: &HashMap<ItemId, ItemId>,
) {
    let scope = ModuleScope {
        module_path: module_path.to_vec(),
        imports: collect_imports(items),
    };
    for item in items {
        match item {
            Item::Function(function) => {
                rewrite_specialization_calls_in_block(&mut function.body, &scope, replacements)
            }
            Item::Impl(impl_block) => {
                for impl_item in &mut impl_block.items {
                    match impl_item {
                        ImplItem::Method(method) => rewrite_specialization_calls_in_block(
                            &mut method.body,
                            &scope,
                            replacements,
                        ),
                        ImplItem::AssocConst(_, _, expr) => {
                            rewrite_specialization_calls_in_expr(expr, &scope, replacements)
                        }
                        ImplItem::AssocType(_, _) => {}
                    }
                }
            }
            Item::Const(const_def) => {
                rewrite_specialization_calls_in_expr(&mut const_def.value, &scope, replacements)
            }
            Item::LazyStatic(lazy_static) => {
                rewrite_specialization_calls_in_block(&mut lazy_static.init, &scope, replacements)
            }
            Item::Mod(module) => {
                let mut nested_path = module_path.to_vec();
                nested_path.push(module.name.clone());
                rewrite_specialization_calls_in_items(
                    &mut module.items,
                    &nested_path,
                    replacements,
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

fn rewrite_specialization_calls_in_block(
    block: &mut Block,
    scope: &ModuleScope,
    replacements: &HashMap<ItemId, ItemId>,
) {
    for statement in &mut block.stmts {
        match statement {
            Statement::Let(let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    rewrite_specialization_calls_in_expr(init, scope, replacements);
                }
            }
            Statement::Expr(expr) => {
                rewrite_specialization_calls_in_expr(expr, scope, replacements)
            }
            Statement::Item(item) => rewrite_specialization_calls_in_items(
                std::slice::from_mut(item),
                &scope.module_path,
                replacements,
            ),
            Statement::Continue | Statement::Break | Statement::Comment(_) => {}
        }
    }
    if let Some(expr) = &mut block.expr {
        rewrite_specialization_calls_in_expr(expr, scope, replacements);
    }
}

fn rewrite_specialization_calls_in_expr(
    expr: &mut Expr,
    scope: &ModuleScope,
    replacements: &HashMap<ItemId, ItemId>,
) {
    match expr {
        Expr::Call(callee, args) => {
            rewrite_specialization_calls_in_expr(callee, scope, replacements);
            for arg in args {
                rewrite_specialization_calls_in_expr(arg, scope, replacements);
            }
            let callee_id = match callee.as_ref() {
                Expr::Ident(name) => Some(scope.resolve_name_path(name)),
                Expr::Path(path, PathType::Namespace) => Some(scope.resolve_segments(path)),
                Expr::Parenthesized(inner) => match inner.as_ref() {
                    Expr::Ident(name) => Some(scope.resolve_name_path(name)),
                    Expr::Path(path, PathType::Namespace) => Some(scope.resolve_segments(path)),
                    _ => None,
                },
                _ => None,
            };
            if let Some(original) = callee_id.and_then(|id| replacements.get(&id)) {
                let local = original[..original.len().saturating_sub(1)] == scope.module_path;
                let replacement = if local {
                    Expr::Ident(original.last().cloned().unwrap_or_default())
                } else {
                    Expr::Path(original.clone(), PathType::Namespace)
                };
                **callee = replacement;
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            rewrite_specialization_calls_in_expr(receiver, scope, replacements);
            for arg in args {
                rewrite_specialization_calls_in_expr(arg, scope, replacements);
            }
        }
        Expr::Array(items) | Expr::Tuple(items) => {
            for item in items {
                rewrite_specialization_calls_in_expr(item, scope, replacements);
            }
        }
        Expr::Block(block) => rewrite_specialization_calls_in_block(block, scope, replacements),
        Expr::Loop(block) | Expr::Unsafe(block) => {
            rewrite_specialization_calls_in_block(block, scope, replacements)
        }
        Expr::Closure(_, body, _)
        | Expr::TypedClosure(_, _, body, _)
        | Expr::Await(body)
        | Expr::Parenthesized(body)
        | Expr::Cast(body, _)
        | Expr::UnaryOp(_, body)
        | Expr::Reference(body, _, _) => {
            rewrite_specialization_calls_in_expr(body, scope, replacements)
        }
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            rewrite_specialization_calls_in_expr(condition, scope, replacements);
            rewrite_specialization_calls_in_block(then_branch, scope, replacements);
            if let Some(else_branch) = else_branch {
                rewrite_specialization_calls_in_block(else_branch, scope, replacements);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            rewrite_specialization_calls_in_expr(value, scope, replacements);
            rewrite_specialization_calls_in_block(then_branch, scope, replacements);
            if let Some(else_branch) = else_branch {
                rewrite_specialization_calls_in_block(else_branch, scope, replacements);
            }
        }
        Expr::Match { expr, arms } => {
            rewrite_specialization_calls_in_expr(expr, scope, replacements);
            for arm in arms {
                if let Some(guard) = &mut arm.guard {
                    rewrite_specialization_calls_in_expr(guard, scope, replacements);
                }
                rewrite_specialization_calls_in_block(&mut arm.body, scope, replacements);
            }
        }
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            rewrite_specialization_calls_in_expr(left, scope, replacements);
            rewrite_specialization_calls_in_expr(right, scope, replacements);
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    rewrite_specialization_calls_in_expr(closure, scope, replacements);
                }
            }
        }
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
    }
}

fn count_clone_calls_in_block(block: &Block) -> usize {
    let statements = block
        .stmts
        .iter()
        .map(|statement| match statement {
            Statement::Let(let_stmt) => let_stmt
                .init
                .as_ref()
                .map(count_clone_calls_in_expr)
                .unwrap_or(0),
            Statement::Expr(expr) => count_clone_calls_in_expr(expr),
            Statement::Item(item) => count_clone_calls_in_item(item),
            Statement::Continue | Statement::Break | Statement::Comment(_) => 0,
        })
        .sum::<usize>();
    statements
        + block
            .expr
            .as_ref()
            .map(|expr| count_clone_calls_in_expr(expr))
            .unwrap_or(0)
}

fn count_clone_calls_in_item(item: &Item) -> usize {
    match item {
        Item::Function(function) => count_clone_calls_in_block(&function.body),
        Item::Impl(impl_block) => impl_block
            .items
            .iter()
            .map(|item| match item {
                ImplItem::Method(method) => count_clone_calls_in_block(&method.body),
                ImplItem::AssocConst(_, _, expr) => count_clone_calls_in_expr(expr),
                ImplItem::AssocType(_, _) => 0,
            })
            .sum(),
        Item::Const(const_def) => count_clone_calls_in_expr(&const_def.value),
        Item::LazyStatic(lazy_static) => count_clone_calls_in_block(&lazy_static.init),
        Item::Mod(module) => module.items.iter().map(count_clone_calls_in_item).sum(),
        Item::Raw(_)
        | Item::Struct(_)
        | Item::Enum(_)
        | Item::Union(_)
        | Item::TypeAlias(_)
        | Item::Use(_) => 0,
    }
}

fn count_clone_calls_in_expr(expr: &Expr) -> usize {
    match expr {
        Expr::MethodCall(receiver, method, args) => {
            usize::from(method == "clone" && args.is_empty())
                + count_clone_calls_in_expr(receiver)
                + args.iter().map(count_clone_calls_in_expr).sum::<usize>()
        }
        Expr::Call(callee, args) => {
            count_clone_calls_in_expr(callee)
                + args.iter().map(count_clone_calls_in_expr).sum::<usize>()
        }
        Expr::Array(items) | Expr::Tuple(items) => {
            items.iter().map(count_clone_calls_in_expr).sum()
        }
        Expr::Block(block) => count_clone_calls_in_block(block),
        Expr::Loop(block) | Expr::Unsafe(block) => count_clone_calls_in_block(block),
        Expr::Closure(_, body, _)
        | Expr::TypedClosure(_, _, body, _)
        | Expr::Await(body)
        | Expr::Parenthesized(body)
        | Expr::Cast(body, _)
        | Expr::UnaryOp(_, body)
        | Expr::Reference(body, _, _) => count_clone_calls_in_expr(body),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            count_clone_calls_in_expr(condition)
                + count_clone_calls_in_block(then_branch)
                + else_branch
                    .as_ref()
                    .map(count_clone_calls_in_block)
                    .unwrap_or(0)
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            count_clone_calls_in_expr(value)
                + count_clone_calls_in_block(then_branch)
                + else_branch
                    .as_ref()
                    .map(count_clone_calls_in_block)
                    .unwrap_or(0)
        }
        Expr::Match { expr, arms } => {
            count_clone_calls_in_expr(expr)
                + arms
                    .iter()
                    .map(|arm| {
                        arm.guard
                            .as_ref()
                            .map(count_clone_calls_in_expr)
                            .unwrap_or(0)
                            + count_clone_calls_in_block(&arm.body)
                    })
                    .sum::<usize>()
        }
        Expr::BinaryOp(left, _, right) | Expr::Index(left, right) | Expr::Assign(left, right) => {
            count_clone_calls_in_expr(left) + count_clone_calls_in_expr(right)
        }
        Expr::BuilderChain(methods) => methods
            .iter()
            .map(|method| match method {
                BuilderMethod::Spawn { closure, .. } => count_clone_calls_in_expr(closure),
                _ => 0,
            })
            .sum(),
        Expr::Ident(_) | Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => 0,
    }
}

fn explicit_identity_return_type(callee: &Expr) -> Option<Type> {
    let segment = match callee {
        Expr::Ident(segment) => segment,
        Expr::Path(path, PathType::Namespace) => path.last()?,
        Expr::Parenthesized(inner) => return explicit_identity_return_type(inner),
        _ => return None,
    };
    let name = segment
        .split_once('<')
        .map_or(segment.as_str(), |(head, _)| head)
        .trim()
        .trim_end_matches("::");
    (name == "identity")
        .then(|| crate::rustlight_parser::first_explicit_type_argument(segment))
        .flatten()
}

fn explicit_qself_value_return_type(callee: &Expr) -> Option<Type> {
    let source = match callee {
        Expr::Macro(source) => source.trim(),
        Expr::Parenthesized(inner) => return explicit_qself_value_return_type(inner),
        _ => return None,
    };
    let (receiver, rest) = source.strip_prefix('<')?.split_once(" as ")?;
    let (trait_name, method) = rest.split_once(">::")?;
    let returns_self = matches!(
        (trait_name.trim(), method.trim()),
        ("Zero", "zero")
            | ("One", "one")
            | ("Plus", "plus")
            | ("Minus", "minus")
            | ("Times", "times")
            | ("Divide", "divide")
            | ("Modulo", "modulo")
            | ("Uminus", "uminus")
    );
    returns_self.then(|| Type::Named(receiver.trim().to_string()))
}

fn item_id(scope: &ModuleScope, name: &str) -> ItemId {
    let mut id = scope.module_path.clone();
    id.push(name.to_string());
    id
}

fn type_is_copy_trait(ty: &Type) -> bool {
    match ty {
        Type::Named(name) => name == "Copy",
        Type::Path(path) => path.last().is_some_and(|name| name == "Copy"),
        _ => false,
    }
}

fn type_constructor_id(ty: &Type, scope: &ModuleScope) -> Option<ItemId> {
    match ty {
        Type::Named(name) => Some(scope.resolve_name_path(name)),
        Type::Generic(name, _) => Some(resolve_type_constructor_name(name, scope)),
        Type::Path(path) => Some(scope.resolve_segments(path)),
        _ => None,
    }
}

fn type_leaf_name(ty: &Type) -> Option<&str> {
    match ty {
        Type::Named(name) => Some(name),
        Type::Generic(name, _) => Some(type_name_leaf(name)),
        Type::Path(path) => path.last().map(String::as_str),
        _ => None,
    }
}

fn type_name_leaf(name: &str) -> &str {
    name.rsplit("::").next().unwrap_or(name)
}

fn resolve_type_constructor_name(name: &str, scope: &ModuleScope) -> ItemId {
    if name.contains("::") {
        let segments = name.split("::").map(str::to_string).collect::<Vec<_>>();
        scope.resolve_segments(&segments)
    } else {
        scope.resolve_name_path(name)
    }
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
    generic_param_names_with_bound(&function.generics, bound)
}

fn generic_param_names_with_bound(generics: &[GenericParam], bound: &str) -> HashSet<String> {
    generics
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

fn closure_param_pattern(param: &ClosureParam) -> String {
    param.pattern.trim().to_string()
}

fn closure_param_type(param: &ClosureParam) -> Option<Type> {
    param.ty.clone()
}

fn remove_pattern_types(pattern: &str, env: &mut TypeEnv) {
    let names = env.keys().cloned().collect::<Vec<_>>();
    for name in names {
        if pattern_binding_tokens(pattern).any(|token| token == name) {
            env.remove(&name);
        }
    }
}

fn pattern_binding_tokens(pattern: &str) -> impl Iterator<Item = &str> {
    pattern
        .split(|ch: char| !(ch == '_' || ch.is_ascii_alphanumeric()))
        .filter(|token| {
            is_binding_ident(token)
                && !token
                    .chars()
                    .next()
                    .is_some_and(|ch| ch.is_ascii_uppercase())
        })
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
            Type::Generic(aname, aparams)
                if type_name_leaf(name) == type_name_leaf(aname)
                    && params.len() == aparams.len() =>
            {
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
                ..CopyOptions::default()
            },
        );
        assert!(printed.contains("pub fn dup_copy"));
        assert!(printed.contains("Copy-specialized bounds"));
    }

    #[test]
    fn tightens_original_when_every_reachable_call_is_copy() {
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
        assert!(printed.contains("globally tightened Copy bounds"));
        assert!(!printed.contains("pub fn dup_copy"));
        assert!(!printed.contains("x.clone()"));
        assert!(printed.contains("dup(x)"));
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
        assert!(printed.contains("globally tightened Copy bounds"));
        assert!(!printed.contains("pub fn duplicate_first_copy"));
        assert!(printed.contains("duplicate_first(x, other)"));
        assert!(printed.contains("B: Clone"));
    }

    #[test]
    fn copy_call_uses_known_arguments_when_an_unrelated_argument_is_opaque() {
        let source = r#"
pub fn select<A>(x: A, n: usize) -> A
where
    A: Clone + 'static
{
    x.clone()
}

pub fn use_select(x: bool, n: usize) -> bool {
    select(x, n + 1usize)
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("globally tightened Copy bounds"));
        assert!(!printed.contains("pub fn select_copy"));
        assert!(printed.contains("select(x, n + 1usize)"));
    }

    #[test]
    fn retains_specialization_only_for_mixed_copy_and_noncopy_calls() {
        let source = r#"
pub fn dup<A>(x: A) -> (A, A)
where A: Clone + 'static
{
    (x.clone(), x.clone())
}

pub fn use_copy(x: bool) -> (bool, bool) {
    dup(x)
}

pub fn use_clone(x: String) -> (String, String) {
    dup(x)
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("pub fn dup_copy"));
        assert!(printed.contains("dup_copy(x)"));
        assert!(printed.contains("pub fn use_clone"));
        assert!(printed.contains("dup(x)"));
    }

    #[test]
    fn retained_generic_wrapper_keeps_clone_callee_reachable() {
        let source = r#"
pub fn dup<A>(x: A) -> (A, A)
where A: Clone + 'static
{
    (x.clone(), x.clone())
}

pub fn use_copy(x: bool) -> (bool, bool) {
    dup(x)
}

pub fn generic_wrapper<A>(x: A) -> (A, A)
where A: Clone + 'static
{
    dup(x)
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("pub fn dup_copy"));
        assert!(printed.contains("dup_copy(x)"));
        assert!(printed.contains("pub fn generic_wrapper"));
        assert!(printed.contains("A: Clone"));
        assert!(printed.contains("dup(x)"));
    }

    #[test]
    fn associated_generic_value_does_not_select_copy_callee() {
        let source = r#"
pub trait Zero {
    fn zero() -> Self;
}

pub fn duplicate<A>(x: A) -> (A, A)
where A: Clone + 'static
{
    (x.clone(), x.clone())
}

pub fn use_copy(x: bool) -> (bool, bool) {
    duplicate(x)
}

pub fn make_pair<A>() -> (A, A)
where A: Clone + Zero + 'static
{
    duplicate(<A as Zero>::zero())
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("pub fn duplicate_copy"));
        assert!(printed.contains("duplicate_copy(x)"));
        assert!(printed.contains("pub fn make_pair"));
        assert!(printed.contains("duplicate(<A as Zero>::zero())"));
    }

    #[test]
    fn keeps_copy_bound_when_borrow_will_decide_a_preserved_match_clone() {
        let source = r#"
pub fn observe<A>(x: A) -> bool
where A: Clone + 'static
{
    match x.clone() {
        _ => true,
    }
}

pub fn observe_copy(x: bool) -> bool {
    observe(x)
}

pub fn observe_clone(x: String) -> bool {
    observe(x)
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("pub fn observe_copy2"));
        let specialization = printed
            .split_once("pub fn observe_copy2")
            .expect("mixed Copy specialization")
            .1
            .split_once("pub fn observe_copy")
            .expect("following caller")
            .0;
        assert!(specialization.contains("Copy"));
        assert!(specialization.contains("match x.clone()"));
    }

    #[test]
    fn propagates_effectful_specializations_but_not_inert_duplicates() {
        let source = r#"
pub fn duplicate<A>(x: A) -> (A, A)
where A: Clone + 'static
{
    (x.clone(), x.clone())
}

pub fn wrapper<A>(x: A) -> (A, A)
where A: Clone + 'static
{
    duplicate(x)
}

pub fn use_copy(x: bool) -> (bool, bool) {
    wrapper(x)
}

pub fn use_clone(x: String) -> (String, String) {
    wrapper(x)
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("pub fn duplicate_copy"));
        assert!(printed.contains("pub fn wrapper_copy"));
        assert!(printed.contains("duplicate_copy(x)"));
        assert!(printed.contains("wrapper_copy(x)"));
    }

    #[test]
    fn all_copy_wrapper_chain_is_folded_into_originals() {
        let source = r#"
pub fn duplicate<A>(x: A) -> (A, A)
where A: Clone + 'static
{
    (x.clone(), x.clone())
}

pub fn wrapper<A>(x: A) -> (A, A)
where A: Clone + 'static
{
    duplicate(x)
}

pub fn use_wrapper(x: bool) -> (bool, bool) {
    wrapper(x)
}
"#;

        let printed = optimize_and_print(source);
        assert!(!printed.contains("pub fn duplicate_copy"));
        assert!(!printed.contains("pub fn wrapper_copy"));
        assert!(printed.matches("globally tightened Copy bounds").count() >= 2);
        assert!(printed.contains("duplicate(x)"));
        assert!(printed.contains("wrapper(x)"));
    }

    #[test]
    fn unused_candidate_is_removed_even_when_it_could_delete_clone() {
        let source = r#"
pub fn unused<A>(x: A) -> A
where A: Clone + 'static
{
    x.clone()
}
"#;

        let printed = optimize_and_print(source);
        assert!(!printed.contains("unused_copy"));
        assert!(printed.contains("A: Clone"));
        assert!(printed.contains("x.clone()"));
    }

    #[test]
    fn no_specialization_is_created_without_a_real_copy_effect() {
        let source = r#"
pub fn identity<A>(x: A) -> A
where A: Clone + 'static
{
    x
}

pub fn use_identity(x: bool) -> bool {
    identity(x)
}
"#;

        let printed = optimize_and_print_with_options(
            source,
            CopyOptions {
                keep_unused_copy: true,
                ..CopyOptions::default()
            },
        );
        assert!(!printed.contains("identity_copy"));
        assert!(printed.contains("A: Clone"));
    }

    #[test]
    fn copy_and_noncopy_call_paths_keep_original_and_specialization_distinct() {
        let source = r#"
pub fn take<A>(x: A) -> A
where A: Clone + 'static
{
    x.clone()
}

pub fn take_bool(x: bool) -> bool {
    take(x)
}

pub fn take_string(x: String) -> String {
    take(x)
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("pub fn take_copy"));
        assert!(printed.contains("take_copy(x)"));
        assert!(printed.contains("take(x)"));
        let original = printed
            .split_once("pub fn take<A>")
            .expect("original function")
            .1
            .split_once("pub fn take_copy")
            .expect("specialization follows original")
            .0;
        assert!(original.contains("Clone"));
        assert!(original.contains("x.clone()"));
    }

    #[test]
    fn tightened_original_does_not_leave_a_second_copy_function() {
        let source = r#"
pub fn take<A>(x: A) -> A
where A: Clone + 'static
{
    x.clone()
}

pub fn take_bool(x: bool) -> bool {
    take(x)
}
"#;

        let printed = optimize_and_print(source);
        assert!(!printed.contains("pub fn take_copy"));
        assert!(printed.contains("globally tightened Copy bounds"));
        assert!(!printed.contains("x.clone()"));
    }

    #[test]
    fn mixed_call_specialization_removes_clone_in_its_own_body() {
        let source = r#"
pub fn take<A>(x: A) -> A
where A: Clone + 'static
{
    x.clone()
}

pub fn take_bool(x: bool) -> bool { take(x) }
pub fn take_string(x: String) -> String { take(x) }
"#;

        let printed = optimize_and_print(source);
        let specialization = printed
            .split_once("pub fn take_copy")
            .expect("copy specialization")
            .1
            .split_once("pub fn take_bool")
            .expect("following function")
            .0;
        assert!(!specialization.contains("clone"));
    }

    #[test]
    fn specialization_names_remain_collision_safe_after_mode_selection() {
        let source = r#"
pub fn take_copy(x: bool) -> bool { x }

pub fn take<A>(x: A) -> A
where A: Clone + 'static
{
    x.clone()
}

pub fn take_bool(x: bool) -> bool { take(x) }
pub fn take_string(x: String) -> String { take(x) }
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("pub fn take_copy2"));
        assert!(printed.contains("take_copy2(x)"));
    }

    #[test]
    fn all_copy_fold_preserves_unrelated_existing_copy_function() {
        let source = r#"
pub fn take_copy(x: bool) -> bool { x }

pub fn take<A>(x: A) -> A
where A: Clone + 'static
{
    x.clone()
}

pub fn take_bool(x: bool) -> bool { take(x) }
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("pub fn take_copy(x: bool)"));
        assert!(!printed.contains("pub fn take_copy2"));
        assert!(printed.contains("globally tightened Copy bounds"));
    }

    #[test]
    fn copy_bound_tightening_does_not_change_unrelated_clone_bounds() {
        let source = r#"
pub fn first<A, B>(x: A, y: B) -> (A, B)
where A: Clone + 'static, B: Clone + 'static
{
    (x.clone(), y)
}

pub fn first_bool(x: bool, y: String) -> (bool, String) {
    first(x, y)
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("B: Clone"));
        assert!(!printed.contains("pub fn first_copy"));
        assert!(!printed.contains("x.clone()"));
    }

    #[test]
    fn noncopy_only_calls_do_not_keep_copy_specialization() {
        let source = r#"
pub fn take<A>(x: A) -> A
where A: Clone + 'static
{
    x.clone()
}

pub fn take_string(x: String) -> String {
    take(x)
}
"#;

        let printed = optimize_and_print(source);
        assert!(!printed.contains("pub fn take_copy"));
        assert!(printed.contains("A: Clone"));
        assert!(printed.contains("x.clone()"));
    }

    #[test]
    fn recursive_all_copy_function_is_tightened_once() {
        let source = r#"
pub fn repeat<A>(x: A, n: usize) -> A
where A: Clone + 'static
{
    if n == 0usize {
        x.clone()
    } else {
        repeat(x, n - 1usize)
    }
}

pub fn repeat_bool(x: bool, n: usize) -> bool {
    repeat(x, n)
}
"#;

        let printed = optimize_and_print(source);
        assert!(!printed.contains("pub fn repeat_copy"));
        assert!(printed.contains("globally tightened Copy bounds"));
        assert!(printed.contains("repeat(x, n - 1usize)"));
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
    fn infers_copy_result_from_qualified_numeric_trait_call() {
        let source = r#"
pub fn quotient(a: i128, b: i128) -> i128 {
    let c = <i128 as Divide>::divide(a, b);
    c.clone()
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("<i128 as Divide>::divide(a, b)"));
        assert!(!printed.contains("c.clone()"));
    }

    #[test]
    fn removes_copy_clones_inside_impl_methods() {
        let source = r#"
pub struct Marker {}

impl Marker {
    pub fn duplicate(x: bool) -> (bool, bool) {
        (x.clone(), x.clone())
    }
}

pub struct Holder<A> {
    pub value: A,
}

impl<A: Copy> Holder<A> {
    pub fn duplicate_value(x: A) -> (A, A) {
        (x.clone(), x.clone())
    }
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("(x, x)"));
        assert!(!printed.contains("x.clone()"));
    }

    #[test]
    fn binds_typed_tuple_closure_parameters_before_clone_rewrite() {
        let source = r#"
use std::rc::Rc;

pub fn make_checker()
    -> Rc<dyn Fn((bool, Rc<dyn Fn(()) -> bool>)) -> bool>
{
    Rc::new(move |(flag, callback): (bool, Rc<dyn Fn(()) -> bool>)| -> bool {
        let _ = callback;
        flag.clone()
    })
}
"#;

        let printed = optimize_and_print(source);
        assert!(!printed.contains("flag.clone()"));
    }

    #[test]
    fn infers_if_tail_type_for_tuple_pattern_clone_rewrite() {
        let source = r#"
pub fn choose(gamma: bool, left: String, right: String) -> bool {
    let (selected, (_left, _right)) = if gamma {
        let flipped = !gamma;
        (flipped, (left, right))
    } else {
        (gamma, (right, left))
    };
    selected.clone()
}
"#;

        let printed = optimize_and_print(source);
        assert!(!printed.contains("selected.clone()"));
    }

    #[test]
    fn keeps_clone_when_if_branch_type_is_not_proven() {
        let source = r#"
pub fn choose_or_stop(gamma: bool) -> bool {
    let selected = if gamma {
        true
    } else {
        panic!("stop")
    };
    selected.clone()
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("selected.clone()"));
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
            assert!(analysis.inferred_copy_types.contains("Char"));
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
        assert!(!callee.contains("pub fn duplicate_copy"));
        assert!(callee.contains("globally tightened Copy bounds"));
        assert!(caller.contains("crate::Callee::duplicate(x)"));
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
        assert!(!analysis.inferred_copy_types.contains("Token"));
    }

    #[test]
    fn explicit_unconditional_copy_impl_removes_clone_without_copy_marker_bound() {
        let source = r#"
use std::marker::PhantomData;

#[derive(Clone)]
pub struct Marker(pub Box<bool>);

pub struct Word<W> {
    bits: u128,
    marker: PhantomData<W>,
}

impl<W> Copy for Word<W> {}

impl<W> Clone for Word<W> {
    fn clone(&self) -> Self { *self }
}

pub fn use_word(x: crate::Test::Word<Marker>) -> crate::Test::Word<Marker> {
    let y = std::convert::identity::<crate::Test::Word<Marker>>(x);
    y.clone()
}
"#;

        let printed = optimize_and_print(source);
        assert!(printed.contains("impl<W> Copy for Word<W>"));
        assert!(!printed.contains("#[derive(Clone, Copy)]\npub struct Word"));
        assert!(!printed.contains("y.clone()"));
    }

    #[test]
    fn references_and_phantom_data_follow_standard_copy_semantics() {
        let source = r#"
use std::marker::PhantomData;

pub fn copy_pair<A>(x: (&A, bool)) -> (&A, bool) {
    x.clone()
}

pub fn copy_marker<A>(x: PhantomData<A>) -> PhantomData<A> {
    x.clone()
}
"#;

        let printed = optimize_and_print(source);
        assert!(!printed.contains("x.clone()"));

        let mut module = parse_rust_source(source, "Test").expect("source parses");
        let modules = vec![(vec!["crate".to_string(), "Test".to_string()], &mut module)];
        let ctx = CopyContext::from_modules(&modules);
        let scope = ModuleScope {
            module_path: vec!["crate".to_string(), "Test".to_string()],
            imports: HashMap::new(),
        };
        let shared = Type::Reference(Box::new(Type::Named("bool".to_string())), true, false);
        let mutable = Type::Reference(Box::new(Type::Named("bool".to_string())), true, true);
        assert!(ctx.type_is_copy_in_scope(&shared, &scope, &HashSet::new()));
        assert!(!ctx.type_is_copy_in_scope(&mutable, &scope, &HashSet::new()));
    }

    #[test]
    fn propagates_copy_requirements_through_all_copy_generic_wrappers() {
        let source = r#"
pub fn duplicate<A>(x: A) -> (A, A)
where A: Clone + 'static
{
    (x.clone(), x.clone())
}

pub fn wrapper<A>(x: A) -> (A, A)
where A: Clone + 'static
{
    duplicate(x)
}

pub fn use_wrapper(x: bool) -> (bool, bool) {
    wrapper(x)
}
"#;

        let printed = optimize_and_print(source);
        assert!(!printed.contains("pub fn duplicate_copy"));
        assert!(!printed.contains("pub fn wrapper_copy"));
        assert!(printed.matches("globally tightened Copy bounds").count() >= 2);
        assert!(printed.contains("duplicate(x)"));
        assert!(printed.contains("wrapper(x)"));
    }
}
