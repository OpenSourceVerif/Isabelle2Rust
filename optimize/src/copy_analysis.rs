use std::collections::{HashMap, HashSet};

use rustlightast::*;

/// Result of the copy-analysis pass.
#[derive(Debug, Clone, Default)]
pub struct CopyAnalysis {
    pub copy_types: HashSet<String>,
}

type TypeEnv = HashMap<String, Type>;

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
}

struct CopyContext {
    copy_types: HashSet<String>,
    type_defs: HashMap<String, TypeDef>,
    type_aliases: HashMap<String, Type>,
    variant_owners: HashMap<String, Option<String>>,
    functions: HashMap<String, Type>,
    // Full signatures for R-Call: generic params + parameter types
    fn_sigs: HashMap<String, (Vec<GenericParam>, Vec<Type>)>,
}

/// Infer Copy data types for the Rust fragment generated from Isabelle/HOL,
/// add Copy derives, and remove redundant `.clone()` calls whose receiver has
/// a statically known Copy type.
///
/// This pass intentionally stays on the paper's copy-inference side of the
/// pipeline: it does not optimize borrow/reference expressions or method/impl
/// bodies, which belong to later optimization stages.
pub fn optimize_copy(module: &mut RustModule) -> CopyAnalysis {
    let mut analysis = CopyAnalysis::default();
    optimize_module(module, &mut analysis);
    analysis
}

fn optimize_module(module: &mut RustModule, analysis: &mut CopyAnalysis) {
    let mut ctx = CopyContext::from_items(&module.items);

    // The pass is deliberately staged: infer all local Copy candidates first,
    // then mutate derives/function bodies using that fixed module-local view.
    ctx.infer_copy_types();
    ctx.apply_copy_derives(&mut module.items);
    ctx.add_copy_specializations(&mut module.items);
    ctx.rewrite_items(&mut module.items);

    analysis.copy_types.extend(ctx.copy_types.iter().cloned());

    for item in &mut module.items {
        if let Item::Mod(module) = item {
            optimize_module(module, analysis);
        }
    }
}

impl CopyContext {
    fn from_items(items: &[Item]) -> Self {
        let mut ctx = Self {
            copy_types: HashSet::from([
                // C-Prim: all Rust primitive Copy types
                "bool".to_string(),
                "char".to_string(),
                "u8".to_string(),
                "u16".to_string(),
                "u32".to_string(),
                "u64".to_string(),
                "u128".to_string(),
                "i8".to_string(),
                "i16".to_string(),
                "i32".to_string(),
                "i64".to_string(),
                "i128".to_string(),
                "usize".to_string(),
                "isize".to_string(),
                "f32".to_string(),
                "f64".to_string(),
            ]),
            type_defs: HashMap::new(),
            type_aliases: HashMap::new(),
            variant_owners: HashMap::new(),
            functions: HashMap::new(),
            fn_sigs: HashMap::new(),
        };

        for item in items {
            ctx.collect_item(item);
        }

        ctx
    }

    fn collect_item(&mut self, item: &Item) {
        match item {
            Item::Struct(def) => {
                self.type_defs.insert(
                    def.name.clone(),
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
                    },
                );
            }
            Item::Enum(def) => {
                for variant in &def.variants {
                    self.insert_variant_owner(&variant.name, &def.name);
                }

                self.type_defs.insert(
                    def.name.clone(),
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
                    },
                );
            }
            Item::TypeAlias(alias) => {
                self.type_aliases
                    .insert(alias.name.clone(), alias.target.clone());
            }
            Item::Function(function) => {
                self.functions
                    .insert(function.name.clone(), function.return_type.clone());
                self.fn_sigs.insert(
                    function.name.clone(),
                    (
                        function.generics.clone(),
                        function.params.iter().map(|p| p.ty.clone()).collect(),
                    ),
                );
            }
            _ => {}
        }
    }

    fn insert_variant_owner(&mut self, variant_name: &str, owner_name: &str) {
        self.variant_owners
            .entry(variant_name.to_string())
            .and_modify(|existing| {
                if existing.as_deref() != Some(owner_name) {
                    *existing = None;
                }
            })
            .or_insert_with(|| Some(owner_name.to_string()));
    }

    fn infer_copy_types(&mut self) {
        let mut changed = true;

        // Type aliases and algebraic data types can be mutually dependent, so
        // compute the least fixed point of "all contained fields are Copy".
        while changed {
            changed = false;

            for (name, target) in &self.type_aliases {
                if !self.copy_types.contains(name) && self.type_is_copy(target) {
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
                .all(|field| self.type_is_copy_in_env(&field.ty, &env)),
            TypeDefKind::Enum(variants) => variants.iter().all(|variant| {
                variant
                    .fields
                    .iter()
                    .all(|ty| self.type_is_copy_in_env(ty, &env))
            }),
        }
    }

    fn type_is_copy(&self, ty: &Type) -> bool {
        self.type_is_copy_in_env(ty, &HashSet::new())
    }

    fn type_is_copy_in_env(&self, ty: &Type, copy_generics: &HashSet<String>) -> bool {
        match ty {
            Type::Named(name) => self.copy_types.contains(name) || copy_generics.contains(name),
            Type::Path(path) => path
                .last()
                .is_some_and(|name| self.copy_types.contains(name)),
            Type::Generic(name, params) => {
                self.copy_types.contains(name)
                    && params
                        .iter()
                        .all(|param| self.type_is_copy_in_env(param, copy_generics))
            }
            Type::Tuple(types) => types
                .iter()
                .all(|ty| self.type_is_copy_in_env(ty, copy_generics)),
            Type::Array(inner, _) => self.type_is_copy_in_env(inner, copy_generics),
            Type::Unit | Type::Never => true,
            Type::Reference(_, _, _) => false,
            Type::Slice(_) => false,
        }
    }

    fn apply_copy_derives(&self, items: &mut [Item]) {
        for item in items {
            match item {
                Item::Struct(def) if self.copy_types.contains(&def.name) => {
                    ensure_clone_copy_derives(&mut def.derives);
                }
                Item::Enum(def) if self.copy_types.contains(&def.name) => {
                    ensure_clone_copy_derives(&mut def.derives);
                }
                _ => {}
            }
        }
    }

    fn rewrite_items(&self, items: &mut [Item]) {
        for item in items {
            self.rewrite_item(item);
        }
    }

    fn add_copy_specializations(&mut self, items: &mut Vec<Item>) {
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
                    let specialization = self
                        .copy_specialization_for_function(function, &mut existing_function_names);
                    items.push(item);
                    if let Some(specialization) = specialization {
                        // Register the _copy variant's signature so R-Call can redirect to it.
                        self.functions
                            .insert(specialization.name.clone(), specialization.return_type.clone());
                        self.fn_sigs.insert(
                            specialization.name.clone(),
                            (
                                specialization.generics.clone(),
                                specialization.params.iter().map(|p| p.ty.clone()).collect(),
                            ),
                        );
                        items.push(Item::Function(specialization));
                    }
                }
                _ => items.push(item),
            }
        }
    }

    fn copy_specialization_for_function(
        &self,
        function: &FunctionDef,
        existing_names: &mut HashSet<String>,
    ) -> Option<FunctionDef> {
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
            &clone_generics,
            &copy_generics,
            &mut copy_bound_candidates,
        );

        if copy_bound_candidates.is_empty() {
            return None;
        }

        let mut specialized = function.clone();
        specialized.name = fresh_copy_specialization_name(&function.name, existing_names);

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

        self.rewrite_block(&mut specialized.body, &mut specialized_env, &copy_generics);

        Some(specialized)
    }

    fn rewrite_item(&self, item: &mut Item) {
        match item {
            Item::Function(function) => self.rewrite_function(function),
            _ => {}
        }
    }

    fn rewrite_function(&self, function: &mut FunctionDef) {
        let mut env = function_type_env(function);

        let copy_generics = generic_names_with_bound(function, "Copy");

        self.rewrite_block(&mut function.body, &mut env, &copy_generics);
    }

    fn rewrite_block(&self, block: &mut Block, env: &mut TypeEnv, copy_generics: &HashSet<String>) {
        for stmt in &mut block.stmts {
            match stmt {
                Statement::Let(let_stmt) => {
                    if let Some(init) = &mut let_stmt.init {
                        self.rewrite_expr(init, env, copy_generics);
                    }

                    // Keep the local type environment precise enough for later
                    // field access and pattern-bound clone receivers.
                    let inferred_ty = let_stmt.ty.clone().or_else(|| {
                        let_stmt
                            .init
                            .as_ref()
                            .and_then(|init| self.infer_expr_type(init, env))
                    });

                    if let Some(ty) = inferred_ty {
                        if is_binding_ident(&let_stmt.name) {
                            env.insert(let_stmt.name.clone(), ty);
                        } else {
                            self.bind_pattern_types(&let_stmt.name, &ty, env);
                        }
                    }
                }
                Statement::Expr(expr) => self.rewrite_expr(expr, env, copy_generics),
                Statement::Item(item) => self.rewrite_item(item),
                Statement::Continue | Statement::Break | Statement::Comment(_) => {}
            }
        }

        if let Some(expr) = &mut block.expr {
            self.rewrite_expr(expr, env, copy_generics);
        }
    }

    fn rewrite_expr(&self, expr: &mut Expr, env: &mut TypeEnv, copy_generics: &HashSet<String>) {
        match expr {
            Expr::Tuple(items) => {
                for item in items {
                    self.rewrite_expr(item, env, copy_generics);
                }
            }
            Expr::Call(callee, args) => {
                self.rewrite_expr(callee, env, copy_generics);
                for arg in &mut *args {
                    self.rewrite_expr(arg, env, copy_generics);
                }
                // R-Call: redirect g(ē) → g_copy(ē) when all Clone-only bounds are Copy
                if let Some(new_name) = self.try_rcall(callee, args, env, copy_generics) {
                    **callee = Expr::Ident(new_name);
                }
            }
            Expr::MethodCall(receiver, method, args) => {
                self.rewrite_expr(receiver, env, copy_generics);
                for arg in &mut *args {
                    self.rewrite_expr(arg, env, copy_generics);
                }

                if method == "clone"
                    && args.is_empty()
                    && self
                        .infer_expr_type(receiver, env)
                        .is_some_and(|ty| self.type_is_copy_in_env(&ty, copy_generics))
                {
                    // For Copy receivers, `x.clone()` is semantically just `x`.
                    *expr = receiver.as_ref().clone();
                }
            }
            Expr::Block(block) => {
                let mut block_env = env.clone();
                self.rewrite_block(block, &mut block_env, copy_generics);
            }
            Expr::If {
                condition,
                then_branch,
                else_branch,
            } => {
                self.rewrite_expr(condition, env, copy_generics);

                let mut then_env = env.clone();
                self.rewrite_block(then_branch, &mut then_env, copy_generics);

                if let Some(else_branch) = else_branch {
                    let mut else_env = env.clone();
                    self.rewrite_block(else_branch, &mut else_env, copy_generics);
                }
            }
            Expr::IfLet {
                pattern,
                value,
                then_branch,
                else_branch,
            } => {
                self.rewrite_expr(value, env, copy_generics);

                let mut then_env = env.clone();
                if let Some(value_ty) = self.infer_expr_type(value, env) {
                    self.bind_pattern_types(pattern, &value_ty, &mut then_env);
                }
                self.rewrite_block(then_branch, &mut then_env, copy_generics);

                if let Some(else_branch) = else_branch {
                    let mut else_env = env.clone();
                    self.rewrite_block(else_branch, &mut else_env, copy_generics);
                }
            }
            Expr::Match { expr, arms } => {
                self.rewrite_expr(expr, env, copy_generics);
                let scrutinee_ty = self.infer_expr_type(expr, env);

                for arm in arms {
                    let mut arm_env = env.clone();

                    if let Some(ty) = &scrutinee_ty {
                        self.bind_pattern_types(&arm.pattern, ty, &mut arm_env);
                    }
                    if let Some(guard) = &mut arm.guard {
                        self.rewrite_expr(guard, &mut arm_env, copy_generics);
                    }

                    self.rewrite_block(&mut arm.body, &mut arm_env, copy_generics);
                }
            }
            Expr::Parenthesized(inner) => self.rewrite_expr(inner, env, copy_generics),
            Expr::BinaryOp(left, _, right) => {
                self.rewrite_expr(left, env, copy_generics);
                self.rewrite_expr(right, env, copy_generics);
            }
            // Constructs outside the generated fragment are left unchanged here.
            Expr::Ident(_)
            | Expr::Path(_, _)
            | Expr::Literal(_)
            | Expr::Loop(_)
            | Expr::Await(_)
            | Expr::Closure(_, _, _)
            | Expr::BuilderChain(_)
            | Expr::Unsafe(_)
            | Expr::Reference(_, _, _)
            | Expr::UnaryOp(_, _)
            | Expr::Index(_, _)
            | Expr::Assign(_, _) => {}
        }
    }

    fn collect_copy_bound_candidates(
        &self,
        block: &Block,
        env: &TypeEnv,
        clone_generics: &HashSet<String>,
        copy_generics: &HashSet<String>,
        out: &mut HashSet<String>,
    ) {
        let mut required_copy_env = copy_generics.clone();
        required_copy_env.extend(clone_generics.iter().cloned());
        // A generic is a candidate only if every clone receiver containing it
        // would become Copy after replacing tracked Clone bounds by Copy.
        self.collect_clone_demands(block, env, clone_generics, Some(&required_copy_env), out);
    }

    fn collect_clone_demands(
        &self,
        block: &Block,
        env: &TypeEnv,
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
                            tracked_generics,
                            required_copy_env,
                            out,
                        );
                    }

                    let inferred_ty = let_stmt.ty.clone().or_else(|| {
                        let_stmt
                            .init
                            .as_ref()
                            .and_then(|init| self.infer_expr_type(init, &block_env))
                    });

                    if let Some(ty) = inferred_ty {
                        if is_binding_ident(&let_stmt.name) {
                            block_env.insert(let_stmt.name.clone(), ty);
                        } else {
                            self.bind_pattern_types(&let_stmt.name, &ty, &mut block_env);
                        }
                    }
                }
                Statement::Expr(expr) => self.collect_clone_demands_expr(
                    expr,
                    &block_env,
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
        tracked_generics: &HashSet<String>,
        required_copy_env: Option<&HashSet<String>>,
        out: &mut HashSet<String>,
    ) {
        match expr {
            Expr::Tuple(items) => {
                for item in items {
                    self.collect_clone_demands_expr(
                        item,
                        env,
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
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                for arg in args {
                    self.collect_clone_demands_expr(
                        arg,
                        env,
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
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                for arg in args {
                    self.collect_clone_demands_expr(
                        arg,
                        env,
                        tracked_generics,
                        required_copy_env,
                        out,
                    );
                }

                if method == "clone" && args.is_empty() {
                    if let Some(ty) = self.infer_expr_type(receiver, env) {
                        let mut names = HashSet::new();
                        generic_names_in_type(&ty, &mut names);
                        names.retain(|name| tracked_generics.contains(name));

                        let admissible = required_copy_env
                            .map(|copy_env| self.type_is_copy_in_env(&ty, copy_env))
                            .unwrap_or(true);

                        if admissible {
                            out.extend(names);
                        }
                    }
                }
            }
            Expr::Block(block) => {
                self.collect_clone_demands(block, env, tracked_generics, required_copy_env, out);
            }
            Expr::If {
                condition,
                then_branch,
                else_branch,
            } => {
                self.collect_clone_demands_expr(
                    condition,
                    env,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                self.collect_clone_demands(
                    then_branch,
                    env,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                if let Some(else_branch) = else_branch {
                    self.collect_clone_demands(
                        else_branch,
                        env,
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
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                let mut then_env = env.clone();
                if let Some(value_ty) = self.infer_expr_type(value, env) {
                    self.bind_pattern_types(pattern, &value_ty, &mut then_env);
                }
                self.collect_clone_demands(
                    then_branch,
                    &then_env,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                if let Some(else_branch) = else_branch {
                    self.collect_clone_demands(
                        else_branch,
                        env,
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
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                let scrutinee_ty = self.infer_expr_type(expr, env);
                for arm in arms {
                    let mut arm_env = env.clone();
                    if let Some(ty) = &scrutinee_ty {
                        self.bind_pattern_types(&arm.pattern, ty, &mut arm_env);
                    }
                    if let Some(guard) = &arm.guard {
                        self.collect_clone_demands_expr(
                            guard,
                            &arm_env,
                            tracked_generics,
                            required_copy_env,
                            out,
                        );
                    }
                    self.collect_clone_demands(
                        &arm.body,
                        &arm_env,
                        tracked_generics,
                        required_copy_env,
                        out,
                    );
                }
            }
            Expr::Parenthesized(inner) => self.collect_clone_demands_expr(
                inner,
                env,
                tracked_generics,
                required_copy_env,
                out,
            ),
            Expr::BinaryOp(left, _, right) => {
                self.collect_clone_demands_expr(
                    left,
                    env,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
                self.collect_clone_demands_expr(
                    right,
                    env,
                    tracked_generics,
                    required_copy_env,
                    out,
                );
            }
            // Clone calls under unsupported Rust constructs do not participate
            // in copy-specialization inference.
            Expr::Ident(_)
            | Expr::Path(_, _)
            | Expr::Literal(_)
            | Expr::Loop(_)
            | Expr::Await(_)
            | Expr::Closure(_, _, _)
            | Expr::BuilderChain(_)
            | Expr::Unsafe(_)
            | Expr::Reference(_, _, _)
            | Expr::UnaryOp(_, _)
            | Expr::Index(_, _)
            | Expr::Assign(_, _) => {}
        }
    }

    // R-Call: if callee g has a _copy variant and all Clone-only bounded generics
    // resolve to Copy types at this call site, return the _copy variant name.
    fn try_rcall(
        &self,
        callee: &Expr,
        args: &[Expr],
        env: &TypeEnv,
        copy_generics: &HashSet<String>,
    ) -> Option<String> {
        let fn_name = match callee {
            Expr::Ident(name) => name.as_str(),
            _ => return None,
        };

        // Already a _copy variant — don't chain-redirect.
        if fn_name.ends_with("_copy") {
            return None;
        }

        let copy_name = format!("{fn_name}_copy");
        if !self.functions.contains_key(&copy_name) {
            return None;
        }

        let (generics, param_types) = self.fn_sigs.get(fn_name)?;

        if args.len() != param_types.len() {
            return None;
        }

        let callee_generic_names: HashSet<String> =
            generics.iter().map(|g| g.name.clone()).collect();

        let clone_only: Vec<&str> = generics
            .iter()
            .filter(|g| has_bound(g, "Clone") && !has_bound(g, "Copy"))
            .map(|g| g.name.as_str())
            .collect();

        if clone_only.is_empty() {
            return None;
        }

        // Fast path: we're already inside a copy-specialized context that
        // covers every Clone-only generic the callee needs.  This handles
        // recursive calls like `list_head(List::Nil)` inside `list_head_copy`
        // where the argument type is opaque (no type-arg info to unify on).
        if clone_only.iter().all(|g| copy_generics.contains(*g)) {
            return Some(copy_name);
        }

        let arg_types: Vec<Type> = args
            .iter()
            .map(|a| self.infer_expr_type(a, env))
            .collect::<Option<_>>()?;

        let mut subst = HashMap::new();
        for (formal, actual) in param_types.iter().zip(arg_types.iter()) {
            if !unify_type(formal, actual, &callee_generic_names, &mut subst) {
                return None;
            }
        }

        for alpha in &clone_only {
            let concrete = subst.get(*alpha)?;
            if !self.type_is_copy_in_env(concrete, copy_generics) {
                return None;
            }
        }

        Some(copy_name)
    }

    fn infer_expr_type(&self, expr: &Expr, env: &TypeEnv) -> Option<Type> {
        match expr {
            Expr::Ident(name) => env.get(name).cloned(),
            Expr::Path(path, PathType::Namespace) => self
                .owner_for_variant_path(path)
                .map(Type::Named)
                .or_else(|| {
                    path.last()
                        .and_then(|name| self.functions.get(name).cloned())
                }),
            Expr::Path(path, PathType::Member) => self.infer_member_path_type(path, env),
            Expr::Literal(Literal::Bool(_)) => Some(Type::Named("bool".to_string())),
            Expr::Literal(_) => None,
            Expr::Tuple(items) => {
                let mut types = Vec::new();
                for item in items {
                    types.push(self.infer_expr_type(item, env)?);
                }

                if types.is_empty() {
                    Some(Type::Unit)
                } else {
                    Some(Type::Tuple(types))
                }
            }
            Expr::Call(callee, _) => self.infer_call_type(callee),
            Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
                self.infer_expr_type(receiver, env)
            }
            Expr::Parenthesized(inner) => self.infer_expr_type(inner, env),
            Expr::Block(block) => block
                .expr
                .as_ref()
                .and_then(|expr| self.infer_expr_type(expr, env)),
            Expr::BinaryOp(_, op, _) if binary_op_returns_bool(op) => {
                Some(Type::Named("bool".to_string()))
            }
            _ => None,
        }
    }

    fn infer_call_type(&self, callee: &Expr) -> Option<Type> {
        match callee {
            Expr::Ident(name) => self
                .owner_for_variant_name(name)
                .map(Type::Named)
                .or_else(|| self.functions.get(name).cloned()),
            Expr::Path(path, PathType::Namespace) => self
                .owner_for_variant_path(path)
                .map(Type::Named)
                .or_else(|| {
                    path.last()
                        .and_then(|name| self.functions.get(name).cloned())
                }),
            Expr::Parenthesized(inner) => self.infer_call_type(inner),
            _ => None,
        }
    }

    fn infer_member_path_type(&self, path: &[String], env: &TypeEnv) -> Option<Type> {
        let (head, tail) = path.split_first()?;
        let mut current_ty = env.get(head)?.clone();

        for member in tail {
            current_ty = self.field_type(&current_ty, member)?;
        }

        Some(current_ty)
    }

    fn field_type(&self, ty: &Type, member: &str) -> Option<Type> {
        let type_name = local_type_name(ty)?;
        let def = self.type_defs.get(type_name)?;
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

    fn bind_pattern_types(&self, pattern: &str, expected: &Type, env: &mut TypeEnv) {
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
            self.bind_pattern_types(inner, inner_ty, env);
            return;
        }

        let pattern = strip_binding_modifiers(pattern);

        if let Some(inner) = outer_parens_inner(pattern) {
            let parts = split_top_level_commas(inner);
            if parts.len() > 1 {
                if let Type::Tuple(types) = expected {
                    for (part, ty) in parts.iter().zip(types) {
                        self.bind_pattern_types(part, ty, env);
                    }
                }
                return;
            }
        }

        if let Some((constructor, args)) = split_constructor_pattern(pattern) {
            if let Some(field_types) = self.pattern_payload_types(constructor, expected) {
                for (arg, ty) in args.iter().zip(field_types.iter()) {
                    self.bind_pattern_types(arg, ty, env);
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

    fn pattern_payload_types(&self, constructor: &str, expected: &Type) -> Option<Vec<Type>> {
        let variant_name = constructor
            .rsplit("::")
            .next()
            .unwrap_or(constructor)
            .trim();

        if let Some(expected_name) = local_type_name(expected) {
            if let Some(def) = self.type_defs.get(expected_name) {
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
                        if variant_name == expected_name || constructor.trim() == expected_name =>
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

        let owner = self.owner_for_constructor(constructor)?;
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

    fn owner_for_constructor(&self, constructor: &str) -> Option<String> {
        let parts = constructor
            .split("::")
            .map(str::trim)
            .filter(|part| !part.is_empty())
            .collect::<Vec<_>>();

        if parts.len() >= 2 {
            let owner = parts[parts.len() - 2];
            if self.type_defs.contains_key(owner) {
                return Some(owner.to_string());
            }
        }

        parts
            .last()
            .and_then(|variant_name| self.owner_for_variant_name(variant_name))
    }

    fn owner_for_variant_path(&self, path: &[String]) -> Option<String> {
        if path.len() >= 2 {
            let owner = &path[path.len() - 2];
            let variant_name = path.last()?;

            if self
                .type_defs
                .get(owner)
                .is_some_and(|def| match &def.kind {
                    TypeDefKind::Enum(variants) => {
                        variants.iter().any(|variant| &variant.name == variant_name)
                    }
                    TypeDefKind::Struct(_) => false,
                })
            {
                return Some(owner.clone());
            }
        }

        path.last()
            .and_then(|variant_name| self.owner_for_variant_name(variant_name))
    }

    fn owner_for_variant_name(&self, variant_name: &str) -> Option<String> {
        self.variant_owners.get(variant_name).cloned().flatten()
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

fn local_type_name(ty: &Type) -> Option<&str> {
    match ty {
        Type::Named(name) => Some(name.as_str()),
        Type::Path(path) => path.last().map(String::as_str),
        Type::Generic(name, _) => Some(name.as_str()),
        _ => None,
    }
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
            Type::Tuple(atypes) if ftypes.len() == atypes.len() => {
                ftypes
                    .iter()
                    .zip(atypes)
                    .all(|(f, a)| unify_type(f, a, generic_names, subst))
            }
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
        (Type::Slice(t1), Type::Slice(t2)) => types_equal(t1, t2),
        (Type::Array(t1, n1), Type::Array(t2, n2)) => n1 == n2 && types_equal(t1, t2),
        (Type::Unit, Type::Unit) | (Type::Never, Type::Never) => true,
        _ => false,
    }
}
