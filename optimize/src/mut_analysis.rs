use std::collections::{HashMap, HashSet};

use rustlightast::*;

/// Result of the mutability-inference pass.
#[derive(Debug, Clone, Default)]
pub struct MutAnalysis {
    /// Names of functions in which at least one mut chain was collapsed.
    pub mut_fns: HashSet<String>,
}

/// Collapse clone-based "mut chains" into a single `let mut` binding updated by
/// assignment, and remove the clones that become last-use moves as a result.
///
/// This is the third optimization pass (after copy and borrow).  It implements
/// the three rewrite rules from the paper:
///
///   * **M-Shadow** recovers the shadowed source name.  Thingol prints the
///     successive bindings of one source variable `x` under a deterministic
///     suffix convention (`x`, `xa`, `xb`, …); inverting that convention
///     (`predecessor`) groups the generated names back into one chain and
///     unifies them to a single name.
///   * **M-Mut** turns the unified chain `let x = s0; let x = s1; …` into
///     `let mut x = s0; x = s1; …`.  This is sound because each intermediate
///     value is *confined*: it is never read after the binding that overwrites
///     it (which also discharges the paper's `NoEsc` side condition, since an
///     owned value left unread carries no live borrow past the assignment).
///   * **M-LastUse** rewrites `v.clone()` to `v` wherever `v` is at its last
///     use, which removes the clones the mut rewrite exposes (and any other
///     already-dead clone receiver).
///
/// The pass acts purely on the ownership structure of the binding chain; the
/// right-hand sides are left untouched.
pub fn optimize_mut(module: &mut RustModule) -> MutAnalysis {
    let mut analysis = MutAnalysis::default();
    optimize_module(module, &mut analysis);
    analysis
}

fn optimize_module(module: &mut RustModule, analysis: &mut MutAnalysis) {
    for item in &mut module.items {
        match item {
            Item::Function(function) => {
                if transform_function(function) {
                    analysis.mut_fns.insert(function.name.clone());
                }
            }
            Item::Impl(impl_block) => {
                for impl_item in &mut impl_block.items {
                    if let ImplItem::Method(method) = impl_item {
                        if transform_function(method) {
                            analysis.mut_fns.insert(method.name.clone());
                        }
                    }
                }
            }
            Item::Mod(inner) => optimize_module(inner, analysis),
            _ => {}
        }
    }
}

/// Run the chain transform and last-use elimination over a single function.
/// Returns `true` if a mut chain was collapsed.
fn transform_function(function: &mut FunctionDef) -> bool {
    // M-Shadow + M-Mut: collapse every chain in the body (recursing into nested
    // blocks).  This leaves the clones in place; they are removed next.
    let collapsed = transform_block(&mut function.body);

    // M-LastUse: a scoped backward-liveness pass that turns `v.clone()` into
    // `v` when `v` is owned and not read afterwards. Running it unconditionally
    // is sound, but it only changes anything where clones are genuinely dead.
    let owned = function
        .params
        .iter()
        .filter(|param| !param.name.is_empty() && !is_reference_type(&param.ty))
        .map(|param| param.name.clone())
        .collect();
    let mut live: HashSet<String> = HashSet::new();
    rewrite_lastuse_block(&mut function.body, &mut live, &owned);

    if collapsed {
        ensure_function_comment(function, "// mut-optimized by in-place updates");
    }
    collapsed
}

// ── M-Shadow + M-Mut: mut-chain detection and rewrite ────────────────────────

/// Detect and rewrite every mut chain reachable from `block`, recursing into
/// nested blocks first.  Returns `true` if any chain was collapsed.
fn transform_block(block: &mut Block) -> bool {
    let mut changed = false;

    // Recurse into nested blocks first (match arms, if/else, sub-blocks, …); the
    // Isabelle code generator wraps function bodies in an inner block, so the
    // actual chain usually lives one level down.
    for stmt in &mut block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    changed |= transform_expr(init);
                }
            }
            Statement::Expr(expr) => changed |= transform_expr(expr),
            Statement::Item(item) => {
                if let Item::Function(function) = item.as_mut() {
                    changed |= transform_block(&mut function.body);
                }
            }
            _ => {}
        }
    }
    if let Some(tail) = &mut block.expr {
        changed |= transform_expr(tail);
    }

    // Now collapse chains whose `let` bindings are direct statements of *this*
    // block (so they can be turned into assignments in place).
    changed |= collapse_chains_in_block(block);
    changed
}

fn transform_expr(expr: &mut Expr) -> bool {
    let mut changed = false;
    match expr {
        Expr::Block(block) => changed |= transform_block(block),
        Expr::Loop(block) | Expr::Unsafe(block) => changed |= transform_block(block),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            changed |= transform_expr(condition);
            changed |= transform_block(then_branch);
            if let Some(else_branch) = else_branch {
                changed |= transform_block(else_branch);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            changed |= transform_expr(value);
            changed |= transform_block(then_branch);
            if let Some(else_branch) = else_branch {
                changed |= transform_block(else_branch);
            }
        }
        Expr::Match { expr, arms } => {
            changed |= transform_expr(expr);
            for arm in arms {
                if let Some(guard) = &mut arm.guard {
                    changed |= transform_expr(guard);
                }
                changed |= transform_block(&mut arm.body);
            }
        }
        Expr::Call(callee, args) => {
            changed |= transform_expr(callee);
            for arg in args {
                changed |= transform_expr(arg);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            changed |= transform_expr(receiver);
            for arg in args {
                changed |= transform_expr(arg);
            }
        }
        Expr::Tuple(items) => {
            for item in items {
                changed |= transform_expr(item);
            }
        }
        Expr::BinaryOp(left, _, right) | Expr::Assign(left, right) | Expr::Index(left, right) => {
            changed |= transform_expr(left);
            changed |= transform_expr(right);
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => {
            changed |= transform_expr(inner);
        }
        Expr::Closure(_, body, _) => changed |= transform_expr(body),
        Expr::Ident(_)
        | Expr::Macro(_)
        | Expr::Path(_, _)
        | Expr::Literal(_)
        | Expr::BuilderChain(_) => {}
    }
    changed
}

/// Find every mut chain among the direct `let` statements of `block` and rewrite
/// it to the `let mut` + assignment form.
fn collapse_chains_in_block(block: &mut Block) -> bool {
    let chains = detect_chains(block);
    if chains.is_empty() {
        return false;
    }

    // Combine all chains into one rewrite plan.  Each chain unifies its
    // generated names `x0, x1, …, xn` to `x0` (the first, already-unique name).
    let mut rename_map: HashMap<String, String> = HashMap::new();
    let mut mut_starts: HashSet<usize> = HashSet::new();
    let mut assign_targets: HashMap<usize, String> = HashMap::new();

    for chain in &chains {
        let mut_name = let_binding_name(&block.stmts[chain[0]])
            .expect("chain head is a simple let")
            .to_string();
        mut_starts.insert(chain[0]);
        for &idx in &chain[1..] {
            let name = let_binding_name(&block.stmts[idx])
                .expect("chain element is a simple let")
                .to_string();
            rename_map.insert(name, mut_name.clone());
            assign_targets.insert(idx, mut_name.clone());
        }
    }

    // M-Shadow: rename every *read* of a unified name to the chosen name.  This
    // covers both the handoff uses (in the next element's rhs) and the later
    // uses of the final element in the continuation.
    if !rename_map.is_empty() {
        rename_reads_block(block, &rename_map);
    }

    // M-Mut: the first element becomes `let mut x = s0`; the rest become
    // assignments `x = si`.
    let old_stmts = std::mem::take(&mut block.stmts);
    let mut new_stmts = Vec::with_capacity(old_stmts.len());
    for (idx, stmt) in old_stmts.into_iter().enumerate() {
        if mut_starts.contains(&idx) {
            if let Statement::Let(mut let_stmt) = stmt {
                let_stmt.ifmut = true;
                new_stmts.push(Statement::Let(let_stmt));
            }
        } else if let Some(mut_name) = assign_targets.get(&idx) {
            if let Statement::Let(let_stmt) = stmt {
                let init = let_stmt
                    .init
                    .expect("chain element always has an initialiser");
                new_stmts.push(Statement::Expr(Expr::Assign(
                    Box::new(Expr::Ident(mut_name.clone())),
                    Box::new(init),
                )));
            }
        } else {
            new_stmts.push(stmt);
        }
    }
    block.stmts = new_stmts;

    true
}

/// Detect all mut chains whose bindings are direct statements of `block`.
/// Each returned chain is the ordered list of statement indices `x0, …, xn`
/// (with `n >= 1`, i.e. at least one shadowing binding).
///
/// Identity is recovered from Thingol's deterministic suffix convention: the
/// successive bindings of one source variable `x` are printed `x`, `xa`, `xb`,
/// …, so the predecessor of a generated name is obtained by stripping a trailing
/// `a` (recovering the base) or decrementing a trailing `b`..`z` (see
/// [`predecessor`]).  A link is kept only when the predecessor is *confined* —
/// not read after the successor's binding overwrites it — so collapsing the
/// chain into one in-place update is sound.  A name whose suffix the convention
/// cannot invert (e.g. a single letter) simply forms no link, which is safe: the
/// pass optimizes less, never wrongly.
fn detect_chains(block: &Block) -> Vec<Vec<usize>> {
    // Map each simple-`let` binding name to its statement index.
    let mut name_to_idx: HashMap<String, usize> = HashMap::new();
    for (idx, stmt) in block.stmts.iter().enumerate() {
        if is_simple_let_with_init(stmt) {
            if let Some(name) = let_binding_name(stmt) {
                name_to_idx.insert(name.to_string(), idx);
            }
        }
    }

    // Build predecessor/successor links between binding indices.
    let mut pred_of: HashMap<usize, usize> = HashMap::new();
    let mut succ_of: HashMap<usize, usize> = HashMap::new();

    for (idx, stmt) in block.stmts.iter().enumerate() {
        if !is_simple_let_with_init(stmt) {
            continue;
        }
        let Some(name) = let_binding_name(stmt) else {
            continue;
        };
        let Some(pred_name) = predecessor(name) else {
            continue;
        };
        let Some(&pred_idx) = name_to_idx.get(&pred_name) else {
            continue;
        };
        if pred_idx >= idx {
            continue;
        }
        // Each name must be bound exactly once in this block, so renaming its
        // reads cannot capture an unrelated binding.
        if count_bindings_in_block(block, name) != 1
            || count_bindings_in_block(block, &pred_name) != 1
        {
            continue;
        }
        // Stable box-pattern lowering introduces bindings such as
        // `let uv = *p0a` or, after borrow rewriting,
        // `let uv = p0a.as_ref().clone()`.  These are destructuring artifacts,
        // not shadow updates of the predecessor name.
        if let_init_is_box_extraction(stmt) {
            continue;
        }
        // Confinement: the predecessor's value must not be read after the
        // successor's binding overwrites it.
        if !is_confined(block, &pred_name, idx) {
            continue;
        }
        // `predecessor` is injective on names, so each predecessor index gets at
        // most one successor; guard against an unexpected clash anyway.
        if succ_of.contains_key(&pred_idx) {
            continue;
        }
        pred_of.insert(idx, pred_idx);
        succ_of.insert(pred_idx, idx);
    }

    // Assemble maximal chains from each head: a binding that has a successor but
    // no predecessor link of its own.
    let mut chains = Vec::new();
    for &head in succ_of.keys() {
        if pred_of.contains_key(&head) {
            continue;
        }
        let mut chain = vec![head];
        let mut cur = head;
        while let Some(&next) = succ_of.get(&cur) {
            chain.push(next);
            cur = next;
        }
        if chain.len() >= 2 {
            chains.push(chain);
        }
    }

    chains
}

/// The predecessor of a Thingol-generated shadow name, by inverting its suffix
/// convention: strip a trailing `a` (the first shadow of a base name) or
/// decrement a trailing `b`..`z`.  Returns `None` when the name carries no such
/// suffix, so it cannot be recognized as a shadow continuation.
fn predecessor(name: &str) -> Option<String> {
    let last = name.chars().last()?;
    match last {
        'a' => {
            let base = &name[..name.len() - 1];
            (!base.is_empty()).then(|| base.to_string())
        }
        'b'..='z' => {
            let mut pred = name[..name.len() - 1].to_string();
            pred.push((last as u8 - 1) as char);
            Some(pred)
        }
        _ => None,
    }
}

/// Whether every read of `name` occurs at or before statement index `limit`
/// (the binding that overwrites it).  Reads in the tail expression count as
/// occurring after every statement.
fn is_confined(block: &Block, name: &str, limit: usize) -> bool {
    for (idx, stmt) in block.stmts.iter().enumerate() {
        if idx <= limit {
            continue;
        }
        let reads = match stmt {
            Statement::Let(let_stmt) => let_stmt
                .init
                .as_ref()
                .map_or(0, |init| count_reads_in_expr(init, name)),
            Statement::Expr(expr) => count_reads_in_expr(expr, name),
            _ => 0,
        };
        if reads > 0 {
            return false;
        }
    }
    if let Some(tail) = &block.expr {
        if count_reads_in_expr(tail, name) > 0 {
            return false;
        }
    }
    true
}

// ── M-LastUse: backward-liveness clone elimination ───────────────────────────

/// Whether evaluating `expr` yields an owned (non-reference) value.  Used only
/// as a conservative heuristic for the `owned` set, so unknown shapes return
/// `false`.
fn produces_owned_value(expr: &Expr, owned: &HashSet<String>) -> bool {
    match expr {
        Expr::Ident(name) => owned.contains(name),
        Expr::MethodCall(_, method, args) if method == "clone" && args.is_empty() => true,
        Expr::Call(_, _) => true,
        Expr::Literal(_) => true,
        Expr::Tuple(items) => items.iter().all(|item| produces_owned_value(item, owned)),
        Expr::BinaryOp(_, _, _) => true,
        Expr::UnaryOp(op, inner) if op == "*" => produces_owned_value(inner, owned),
        Expr::Parenthesized(inner) => produces_owned_value(inner, owned),
        Expr::Block(block) => {
            let block_owned = owned_flow_for_block(block, owned)
                .into_iter()
                .last()
                .unwrap_or_else(|| owned.clone());
            block
                .expr
                .as_ref()
                .is_some_and(|tail| produces_owned_value(tail, &block_owned))
        }
        _ => false,
    }
}

fn owned_flow_for_block(block: &Block, inherited: &HashSet<String>) -> Vec<HashSet<String>> {
    let mut current = inherited.clone();
    let mut snapshots = Vec::with_capacity(block.stmts.len() + 1);

    for stmt in &block.stmts {
        snapshots.push(current.clone());
        if let Statement::Let(let_stmt) = stmt {
            let binding_is_owned = match &let_stmt.ty {
                Some(ty) => !is_reference_type(ty),
                None => let_stmt
                    .init
                    .as_ref()
                    .is_some_and(|init| produces_owned_value(init, &current)),
            };
            if binding_is_owned {
                collect_owned_binding_names_from_pattern(&let_stmt.name, &mut current);
            }
        }
    }

    snapshots.push(current);
    snapshots
}

/// Backward-liveness walk of a block: `live` holds the set of variables read in
/// the continuation (everything that executes after this block).  On return,
/// `live` is updated to the variables live on entry to the block.
fn rewrite_lastuse_block(block: &mut Block, live: &mut HashSet<String>, owned: &HashSet<String>) {
    let owned_at = owned_flow_for_block(block, owned);

    // The tail expression executes last.
    if let Some(tail) = &mut block.expr {
        rewrite_lastuse_expr(tail, live, owned_at.last().unwrap_or(owned));
    }

    // Statements execute in source order, so liveness flows backward.
    for (idx, stmt) in block.stmts.iter_mut().enumerate().rev() {
        let stmt_owned = owned_at.get(idx).unwrap_or(owned);
        match stmt {
            Statement::Let(let_stmt) => {
                // The binding kills the name for everything before it.
                remove_pattern_bindings_from_live(&let_stmt.name, live);
                if let Some(init) = &mut let_stmt.init {
                    rewrite_lastuse_expr(init, live, stmt_owned);
                }
            }
            Statement::Expr(expr) => rewrite_lastuse_expr(expr, live, stmt_owned),
            Statement::Item(_) | Statement::Continue | Statement::Break | Statement::Comment(_) => {
            }
        }
    }
}

fn rewrite_lastuse_expr(expr: &mut Expr, live: &mut HashSet<String>, owned: &HashSet<String>) {
    match expr {
        Expr::Ident(name) => {
            live.insert(name.clone());
        }
        Expr::Path(path, PathType::Member) => {
            if let Some(head) = path.first() {
                live.insert(head.clone());
            }
        }
        Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}

        // M-LastUse: `v.clone()` → `v` when `v` is owned and dead afterwards.
        Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
            if let Expr::Ident(var) = receiver.as_ref() {
                let var = var.clone();
                if owned.contains(&var) && !live.contains(&var) {
                    *expr = Expr::Ident(var.clone());
                }
                // Either way this is a read of `var`.
                live.insert(var);
            } else {
                rewrite_lastuse_expr(receiver, live, owned);
            }
        }
        Expr::MethodCall(receiver, _, args) => {
            // Evaluation order is receiver then args, so walk backward.
            for arg in args.iter_mut().rev() {
                rewrite_lastuse_expr(arg, live, owned);
            }
            rewrite_lastuse_expr(receiver, live, owned);
        }
        Expr::Call(callee, args) => {
            for arg in args.iter_mut().rev() {
                rewrite_lastuse_expr(arg, live, owned);
            }
            rewrite_lastuse_expr(callee, live, owned);
        }
        Expr::BinaryOp(left, _, right) => {
            rewrite_lastuse_expr(right, live, owned);
            rewrite_lastuse_expr(left, live, owned);
        }
        Expr::Assign(left, right) => {
            // `x = rhs` overwrites `x`: the old value is dead after this
            // statement, so reads of `x` inside `rhs` are last uses.
            if let Expr::Ident(target) = left.as_ref() {
                live.remove(target);
                rewrite_lastuse_expr(right, live, owned);
            } else {
                rewrite_lastuse_expr(right, live, owned);
                rewrite_lastuse_expr(left, live, owned);
            }
        }
        Expr::Tuple(items) => {
            for item in items.iter_mut().rev() {
                rewrite_lastuse_expr(item, live, owned);
            }
        }
        Expr::Parenthesized(inner) | Expr::UnaryOp(_, inner) => {
            rewrite_lastuse_expr(inner, live, owned)
        }
        Expr::Reference(inner, _, _) => rewrite_lastuse_expr(inner, live, owned),
        Expr::Index(base, index) => {
            rewrite_lastuse_expr(index, live, owned);
            rewrite_lastuse_expr(base, live, owned);
        }
        Expr::Block(block) => rewrite_lastuse_block(block, live, owned),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            let mut then_live = live.clone();
            rewrite_lastuse_block(then_branch, &mut then_live, owned);
            let mut else_live = live.clone();
            if let Some(else_branch) = else_branch {
                rewrite_lastuse_block(else_branch, &mut else_live, owned);
            }
            *live = union(then_live, else_live);
            rewrite_lastuse_expr(condition, live, owned);
        }
        Expr::IfLet {
            pattern,
            value,
            then_branch,
            else_branch,
        } => {
            let mut then_live = live.clone();
            let mut then_owned = owned.clone();
            if produces_owned_value(value, owned) {
                collect_owned_binding_names_from_pattern(pattern, &mut then_owned);
            }
            rewrite_lastuse_block(then_branch, &mut then_live, &then_owned);
            remove_pattern_bindings_from_live(pattern, &mut then_live);

            let mut else_live = live.clone();
            if let Some(else_branch) = else_branch {
                rewrite_lastuse_block(else_branch, &mut else_live, owned);
            }
            *live = union(then_live, else_live);
            rewrite_lastuse_expr(value, live, owned);
        }
        Expr::Match { expr, arms } => {
            let mut merged = HashSet::new();
            let scrutinee_is_owned = produces_owned_value(expr, owned);
            for arm in arms.iter_mut() {
                let mut arm_live = live.clone();
                let mut arm_owned = owned.clone();
                if scrutinee_is_owned {
                    collect_owned_binding_names_from_pattern(&arm.pattern, &mut arm_owned);
                }
                rewrite_lastuse_block(&mut arm.body, &mut arm_live, &arm_owned);
                if let Some(guard) = &mut arm.guard {
                    rewrite_lastuse_expr(guard, &mut arm_live, &arm_owned);
                }
                remove_pattern_bindings_from_live(&arm.pattern, &mut arm_live);
                merged.extend(arm_live);
            }
            *live = merged;
            rewrite_lastuse_expr(expr, live, owned);
        }

        // Constructs whose control flow this pass does not model precisely
        // (loops, closures captured by reference, async, builder chains): treat
        // every variable they mention as live and strip nothing inside them.
        Expr::Loop(block) | Expr::Unsafe(block) => collect_live_block(block, live),
        Expr::Await(inner) => collect_live_expr(inner, live),
        Expr::Closure(params, body, true) => {
            let closure_owned = params
                .iter()
                .filter(|param| closure_param_is_owned(param))
                .map(|param| closure_param_name(param))
                .collect::<HashSet<_>>();
            let mut closure_live = HashSet::new();
            rewrite_lastuse_expr(body, &mut closure_live, &closure_owned);
            collect_live_closure_body(params, body, live);
        }
        Expr::Closure(params, body, false) => collect_live_closure_body(params, body, live),
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    collect_live_expr(closure, live);
                }
            }
        }
    }
}

fn union(mut a: HashSet<String>, b: HashSet<String>) -> HashSet<String> {
    a.extend(b);
    a
}

/// Add every variable read anywhere in `expr` to `live` (used for constructs
/// processed conservatively).
fn collect_live_expr(expr: &Expr, live: &mut HashSet<String>) {
    match expr {
        Expr::Ident(name) => {
            live.insert(name.clone());
        }
        Expr::Path(path, PathType::Member) => {
            if let Some(head) = path.first() {
                live.insert(head.clone());
            }
        }
        Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) => {}
        Expr::Call(callee, args) => {
            collect_live_expr(callee, live);
            args.iter().for_each(|a| collect_live_expr(a, live));
        }
        Expr::MethodCall(receiver, _, args) => {
            collect_live_expr(receiver, live);
            args.iter().for_each(|a| collect_live_expr(a, live));
        }
        Expr::Tuple(items) => items.iter().for_each(|i| collect_live_expr(i, live)),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            collect_live_expr(l, live);
            collect_live_expr(r, live);
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => collect_live_expr(inner, live),
        Expr::Closure(_, body, _) => collect_live_expr(body, live),
        Expr::Block(block) => collect_live_block(block, live),
        Expr::Loop(block) | Expr::Unsafe(block) => collect_live_block(block, live),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            collect_live_expr(condition, live);
            collect_live_block(then_branch, live);
            if let Some(else_branch) = else_branch {
                collect_live_block(else_branch, live);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            collect_live_expr(value, live);
            collect_live_block(then_branch, live);
            if let Some(else_branch) = else_branch {
                collect_live_block(else_branch, live);
            }
        }
        Expr::Match { expr, arms } => {
            collect_live_expr(expr, live);
            for arm in arms {
                if let Some(guard) = &arm.guard {
                    collect_live_expr(guard, live);
                }
                collect_live_block(&arm.body, live);
            }
        }
        Expr::BuilderChain(methods) => {
            for method in methods {
                if let BuilderMethod::Spawn { closure, .. } = method {
                    collect_live_expr(closure, live);
                }
            }
        }
    }
}

fn collect_live_block(block: &Block, live: &mut HashSet<String>) {
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &let_stmt.init {
                    collect_live_expr(init, live);
                }
            }
            Statement::Expr(expr) => collect_live_expr(expr, live),
            _ => {}
        }
    }
    if let Some(tail) = &block.expr {
        collect_live_expr(tail, live);
    }
}

fn collect_live_closure_body(params: &[String], body: &Expr, live: &mut HashSet<String>) {
    let mut body_live = HashSet::new();
    collect_live_expr(body, &mut body_live);
    for param in params {
        body_live.remove(&closure_param_name(param));
    }
    live.extend(body_live);
}

// ── Read counting and renaming ───────────────────────────────────────────────

fn count_reads_in_block(block: &Block, name: &str) -> usize {
    let mut count = 0;
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &let_stmt.init {
                    count += count_reads_in_expr(init, name);
                }
            }
            Statement::Expr(expr) => count += count_reads_in_expr(expr, name),
            _ => {}
        }
    }
    if let Some(tail) = &block.expr {
        count += count_reads_in_expr(tail, name);
    }
    count
}

fn count_reads_in_expr(expr: &Expr, name: &str) -> usize {
    match expr {
        Expr::Ident(id) => usize::from(id == name),
        Expr::Path(path, PathType::Member) => usize::from(path.first().is_some_and(|h| h == name)),
        Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) | Expr::BuilderChain(_) => 0,
        Expr::Call(callee, args) => {
            count_reads_in_expr(callee, name)
                + args
                    .iter()
                    .map(|a| count_reads_in_expr(a, name))
                    .sum::<usize>()
        }
        Expr::MethodCall(receiver, _, args) => {
            count_reads_in_expr(receiver, name)
                + args
                    .iter()
                    .map(|a| count_reads_in_expr(a, name))
                    .sum::<usize>()
        }
        Expr::Tuple(items) => items.iter().map(|i| count_reads_in_expr(i, name)).sum(),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            count_reads_in_expr(l, name) + count_reads_in_expr(r, name)
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => count_reads_in_expr(inner, name),
        Expr::Closure(_, body, _) => count_reads_in_expr(body, name),
        Expr::Block(block) => count_reads_in_block(block, name),
        Expr::Loop(block) | Expr::Unsafe(block) => count_reads_in_block(block, name),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            count_reads_in_expr(condition, name)
                + count_reads_in_block(then_branch, name)
                + else_branch
                    .as_ref()
                    .map_or(0, |b| count_reads_in_block(b, name))
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            count_reads_in_expr(value, name)
                + count_reads_in_block(then_branch, name)
                + else_branch
                    .as_ref()
                    .map_or(0, |b| count_reads_in_block(b, name))
        }
        Expr::Match { expr, arms } => {
            count_reads_in_expr(expr, name)
                + arms
                    .iter()
                    .map(|arm| {
                        arm.guard
                            .as_ref()
                            .map_or(0, |g| count_reads_in_expr(g, name))
                            + count_reads_in_block(&arm.body, name)
                    })
                    .sum::<usize>()
        }
    }
}

/// Count the binding occurrences of `name` within `block` (its own scope).  Used
/// to reject chains whose name is shadowed, since renaming would then be unsafe.
fn count_bindings_in_block(block: &Block, name: &str) -> usize {
    let mut count = 0;
    for stmt in &block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if is_binding_ident(&let_stmt.name) && let_stmt.name == name {
                    count += 1;
                } else if pattern_binds_name(&let_stmt.name, name) {
                    count += 1;
                }
                if let Some(init) = &let_stmt.init {
                    count += count_bindings_in_expr(init, name);
                }
            }
            Statement::Expr(expr) => count += count_bindings_in_expr(expr, name),
            _ => {}
        }
    }
    if let Some(tail) = &block.expr {
        count += count_bindings_in_expr(tail, name);
    }
    count
}

fn count_bindings_in_expr(expr: &Expr, name: &str) -> usize {
    match expr {
        Expr::Block(block) => count_bindings_in_block(block, name),
        Expr::Loop(block) | Expr::Unsafe(block) => count_bindings_in_block(block, name),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            count_bindings_in_expr(condition, name)
                + count_bindings_in_block(then_branch, name)
                + else_branch
                    .as_ref()
                    .map_or(0, |b| count_bindings_in_block(b, name))
        }
        Expr::IfLet {
            pattern,
            value,
            then_branch,
            else_branch,
        } => {
            usize::from(pattern_binds_name(pattern, name))
                + count_bindings_in_expr(value, name)
                + count_bindings_in_block(then_branch, name)
                + else_branch
                    .as_ref()
                    .map_or(0, |b| count_bindings_in_block(b, name))
        }
        Expr::Match { expr, arms } => {
            count_bindings_in_expr(expr, name)
                + arms
                    .iter()
                    .map(|arm| {
                        usize::from(pattern_binds_name(&arm.pattern, name))
                            + arm
                                .guard
                                .as_ref()
                                .map_or(0, |g| count_bindings_in_expr(g, name))
                            + count_bindings_in_block(&arm.body, name)
                    })
                    .sum::<usize>()
        }
        Expr::Closure(params, body, _) => {
            usize::from(params.iter().any(|p| closure_param_name(p) == name))
                + count_bindings_in_expr(body, name)
        }
        Expr::Call(callee, args) => {
            count_bindings_in_expr(callee, name)
                + args
                    .iter()
                    .map(|a| count_bindings_in_expr(a, name))
                    .sum::<usize>()
        }
        Expr::MethodCall(receiver, _, args) => {
            count_bindings_in_expr(receiver, name)
                + args
                    .iter()
                    .map(|a| count_bindings_in_expr(a, name))
                    .sum::<usize>()
        }
        Expr::Tuple(items) => items.iter().map(|i| count_bindings_in_expr(i, name)).sum(),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            count_bindings_in_expr(l, name) + count_bindings_in_expr(r, name)
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => count_bindings_in_expr(inner, name),
        Expr::Ident(_)
        | Expr::Macro(_)
        | Expr::Path(_, _)
        | Expr::Literal(_)
        | Expr::BuilderChain(_) => 0,
    }
}

/// Rename every *read* of a variable named in `map` to its mapped name, leaving
/// binding occurrences (let names, patterns) untouched.
fn rename_reads_block(block: &mut Block, map: &HashMap<String, String>) {
    for stmt in &mut block.stmts {
        match stmt {
            Statement::Let(let_stmt) => {
                if let Some(init) = &mut let_stmt.init {
                    rename_reads_expr(init, map);
                }
            }
            Statement::Expr(expr) => rename_reads_expr(expr, map),
            _ => {}
        }
    }
    if let Some(tail) = &mut block.expr {
        rename_reads_expr(tail, map);
    }
}

fn rename_reads_expr(expr: &mut Expr, map: &HashMap<String, String>) {
    match expr {
        Expr::Ident(name) => {
            if let Some(replacement) = map.get(name) {
                *name = replacement.clone();
            }
        }
        Expr::Path(path, PathType::Member) => {
            if let Some(head) = path.first_mut() {
                if let Some(replacement) = map.get(head) {
                    *head = replacement.clone();
                }
            }
        }
        Expr::Macro(_) | Expr::Path(_, _) | Expr::Literal(_) | Expr::BuilderChain(_) => {}
        Expr::Call(callee, args) => {
            rename_reads_expr(callee, map);
            args.iter_mut().for_each(|a| rename_reads_expr(a, map));
        }
        Expr::MethodCall(receiver, _, args) => {
            rename_reads_expr(receiver, map);
            args.iter_mut().for_each(|a| rename_reads_expr(a, map));
        }
        Expr::Tuple(items) => items.iter_mut().for_each(|i| rename_reads_expr(i, map)),
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            rename_reads_expr(l, map);
            rename_reads_expr(r, map);
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => rename_reads_expr(inner, map),
        Expr::Closure(params, body, _) => {
            // A closure parameter shadows the outer name inside the body.
            let shadowed = params
                .iter()
                .any(|p| map.contains_key(&closure_param_name(p)));
            if !shadowed {
                rename_reads_expr(body, map);
            }
        }
        Expr::Block(block) => rename_reads_block(block, map),
        Expr::Loop(block) | Expr::Unsafe(block) => rename_reads_block(block, map),
        Expr::If {
            condition,
            then_branch,
            else_branch,
        } => {
            rename_reads_expr(condition, map);
            rename_reads_block(then_branch, map);
            if let Some(else_branch) = else_branch {
                rename_reads_block(else_branch, map);
            }
        }
        Expr::IfLet {
            value,
            then_branch,
            else_branch,
            ..
        } => {
            rename_reads_expr(value, map);
            rename_reads_block(then_branch, map);
            if let Some(else_branch) = else_branch {
                rename_reads_block(else_branch, map);
            }
        }
        Expr::Match { expr, arms } => {
            rename_reads_expr(expr, map);
            for arm in arms {
                if let Some(guard) = &mut arm.guard {
                    rename_reads_expr(guard, map);
                }
                rename_reads_block(&mut arm.body, map);
            }
        }
    }
}

// ── Small helpers ─────────────────────────────────────────────────────────────

fn is_simple_let_with_init(stmt: &Statement) -> bool {
    matches!(stmt, Statement::Let(let_stmt)
        if is_binding_ident(&let_stmt.name) && let_stmt.init.is_some())
}

fn let_binding_name(stmt: &Statement) -> Option<&str> {
    match stmt {
        Statement::Let(let_stmt) if is_binding_ident(&let_stmt.name) => Some(&let_stmt.name),
        _ => None,
    }
}

fn let_init_is_box_extraction(stmt: &Statement) -> bool {
    match stmt {
        Statement::Let(let_stmt) => let_stmt.init.as_ref().is_some_and(is_box_extraction_expr),
        _ => false,
    }
}

fn is_box_extraction_expr(expr: &Expr) -> bool {
    match expr {
        Expr::UnaryOp(op, inner) if op == "*" => matches!(inner.as_ref(), Expr::Ident(_)),
        Expr::MethodCall(receiver, method, args) if method == "clone" && args.is_empty() => {
            matches!(
                receiver.as_ref(),
                Expr::MethodCall(as_ref_receiver, as_ref_method, as_ref_args)
                    if as_ref_method == "as_ref"
                        && as_ref_args.is_empty()
                        && matches!(as_ref_receiver.as_ref(), Expr::Ident(_))
            )
        }
        Expr::Parenthesized(inner) => is_box_extraction_expr(inner),
        _ => false,
    }
}

fn is_reference_type(ty: &Type) -> bool {
    matches!(ty, Type::Reference(_, true, _))
}

fn ensure_function_comment(function: &mut FunctionDef, comment: &str) {
    if !function.docs.iter().any(|doc| doc.trim() == comment) {
        function.docs.push(comment.to_string());
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

fn closure_param_is_owned(param: &str) -> bool {
    let name = closure_param_name(param);
    if !is_binding_ident(&name) {
        return false;
    }

    param
        .split_once(':')
        .map(|(_, ty)| !ty.trim().starts_with('&'))
        .unwrap_or(true)
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

/// Whether the (string) pattern binds a variable called `name`.
fn pattern_binds_name(pattern: &str, name: &str) -> bool {
    if !is_binding_ident(name) {
        return false;
    }
    let mut token = String::new();
    for ch in pattern.chars() {
        if ch == '_' || ch.is_ascii_alphanumeric() {
            token.push(ch);
        } else {
            if token == name {
                return true;
            }
            token.clear();
        }
    }
    token == name
}

fn remove_pattern_bindings_from_live(pattern: &str, live: &mut HashSet<String>) {
    let mut bindings = HashSet::new();
    collect_binding_names_from_pattern(pattern, &mut bindings);
    for binding in bindings {
        live.remove(&binding);
    }
}

fn collect_binding_names_from_pattern(pattern: &str, out: &mut HashSet<String>) {
    collect_pattern_binding_names(pattern, out, true);
}

fn collect_owned_binding_names_from_pattern(pattern: &str, out: &mut HashSet<String>) {
    collect_pattern_binding_names(pattern, out, false);
}

fn collect_pattern_binding_names(pattern: &str, out: &mut HashSet<String>, include_ref: bool) {
    let pattern = pattern.trim();
    if pattern.is_empty() || pattern == "_" || pattern == ".." {
        return;
    }

    if let Some(inner) = strip_prefix_word(pattern, "ref") {
        if include_ref {
            collect_pattern_binding_names(inner, out, include_ref);
        }
        return;
    }
    if let Some(inner) = strip_prefix_word(pattern, "mut") {
        collect_pattern_binding_names(inner, out, include_ref);
        return;
    }
    if let Some(inner) = strip_prefix_word(pattern, "box") {
        collect_pattern_binding_names(inner, out, include_ref);
        return;
    }

    if let Some(inner) = outer_parens_inner(pattern) {
        for part in split_top_level_commas(inner) {
            collect_pattern_binding_names(&part, out, include_ref);
        }
        return;
    }

    if let Some((_, args)) = split_constructor_pattern(pattern) {
        for arg in args {
            collect_pattern_binding_names(&arg, out, include_ref);
        }
        return;
    }

    if pattern.contains("::") || matches!(pattern, "true" | "false") {
        return;
    }

    if is_binding_ident(pattern) {
        out.insert(pattern.to_string());
    }
}

fn strip_prefix_word<'a>(input: &'a str, word: &str) -> Option<&'a str> {
    let rest = input.strip_prefix(word)?;
    if rest.starts_with(char::is_whitespace) {
        Some(rest.trim_start())
    } else {
        None
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
    let mut paren = 0usize;
    let mut bracket = 0usize;
    let mut brace = 0usize;

    for (idx, ch) in input.char_indices() {
        match ch {
            '(' => paren += 1,
            ')' => paren = paren.saturating_sub(1),
            '[' => bracket += 1,
            ']' => bracket = bracket.saturating_sub(1),
            '{' => brace += 1,
            '}' => brace = brace.saturating_sub(1),
            ',' if paren == 0 && bracket == 0 && brace == 0 => {
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
    fn lastuse_removes_clone_from_owned_match_let_binding() {
        let arm_body = Block {
            stmts: vec![let_stmt("x", ident("p0"))],
            expr: Some(Box::new(clone_call("x"))),
        };
        let body = block_tail(Expr::Match {
            expr: Box::new(ident("x0")),
            arms: vec![MatchArm {
                pattern: "Aoption::Somea(p0)".to_string(),
                guard: None,
                body: arm_body,
            }],
        });
        let mut module = module_with(function(named("Aoption"), body));

        optimize_mut(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Match { arms, .. }) = function.body.expr.as_deref() else {
            panic!("expected match")
        };
        let Some(tail) = arms[0].body.expr.as_deref() else {
            panic!("expected arm tail")
        };
        assert!(matches!(tail, Expr::Ident(name) if name == "x"));
    }

    #[test]
    fn lastuse_removes_clone_after_owned_box_extraction() {
        let arm_body = Block {
            stmts: vec![let_stmt(
                "bop",
                Expr::UnaryOp("*".to_string(), Box::new(ident("p0"))),
            )],
            expr: Some(Box::new(Expr::Call(
                Box::new(ident("mugetb")),
                vec![clone_call("bop")],
            ))),
        };
        let body = block_tail(Expr::Match {
            expr: Box::new(ident("x0")),
            arms: vec![MatchArm {
                pattern: "Aoption::MutualReca(p0)".to_string(),
                guard: None,
                body: arm_body,
            }],
        });
        let mut module = module_with(function(named("Aoption"), body));

        optimize_mut(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Match { arms, .. }) = function.body.expr.as_deref() else {
            panic!("expected match")
        };
        let Some(Expr::Call(_, args)) = arms[0].body.expr.as_deref() else {
            panic!("expected call")
        };
        assert!(matches!(&args[0], Expr::Ident(name) if name == "bop"));
    }

    #[test]
    fn lastuse_keeps_clone_from_borrowed_match_binding() {
        let arm_body = block_tail(clone_call("p0"));
        let body = block_tail(Expr::Match {
            expr: Box::new(ident("x0")),
            arms: vec![MatchArm {
                pattern: "Aoption::Somea(p0)".to_string(),
                guard: None,
                body: arm_body,
            }],
        });
        let mut module = module_with(function(ref_to(named("Aoption")), body));

        optimize_mut(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Match { arms, .. }) = function.body.expr.as_deref() else {
            panic!("expected match")
        };
        let Some(tail) = arms[0].body.expr.as_deref() else {
            panic!("expected arm tail")
        };
        assert!(matches!(
            tail,
            Expr::MethodCall(receiver, method, args)
                if matches!(receiver.as_ref(), Expr::Ident(name) if name == "p0")
                    && method == "clone"
                    && args.is_empty()
        ));
    }

    #[test]
    fn lastuse_keeps_clone_from_borrowed_tuple_match_binding() {
        let arm_body = block_tail(clone_call("p0"));
        let body = block_tail(Expr::Match {
            expr: Box::new(Expr::Tuple(vec![ident("x0"), ident("y0")])),
            arms: vec![MatchArm {
                pattern: "(Aoption::Somea(p0), _)".to_string(),
                guard: None,
                body: arm_body,
            }],
        });
        let mut function = function(ref_to(named("Aoption")), body);
        function.params.push(Param {
            name: "y0".to_string(),
            ty: ref_to(named("Aoption")),
        });
        let mut module = module_with(function);

        optimize_mut(&mut module);

        let function = optimized_function(&module);
        let Some(Expr::Match { arms, .. }) = function.body.expr.as_deref() else {
            panic!("expected match")
        };
        let Some(tail) = arms[0].body.expr.as_deref() else {
            panic!("expected arm tail")
        };
        assert!(matches!(
            tail,
            Expr::MethodCall(receiver, method, args)
                if matches!(receiver.as_ref(), Expr::Ident(name) if name == "p0")
                    && method == "clone"
                    && args.is_empty()
        ));
    }
}
