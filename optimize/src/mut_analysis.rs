use std::collections::{HashMap, HashSet};

use rustlightast::*;

/// Result of the mutability-inference pass.
#[derive(Debug, Clone, Default)]
pub struct MutAnalysis {
    /// Names of functions in which at least one mut chain was collapsed.
    pub mut_fns: HashSet<String>,
}

/// Recover in-place mutation from Thingol-generated shadow chains.
///
/// The pass implements M-Shadow and M-Mut only. Last-use clone elimination
/// and trailing-binding cleanup are independent passes.
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

/// Run M-Shadow and M-Mut over a single function.
/// Returns `true` if a mut chain was collapsed.
fn transform_function(function: &mut FunctionDef) -> bool {
    let collapsed = transform_block(&mut function.body);
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
        Expr::Array(items) | Expr::Tuple(items) => {
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
        | Expr::Cast(inner, _)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => {
            changed |= transform_expr(inner);
        }
        Expr::Closure(_, body, _) | Expr::TypedClosure(_, _, body, _) => {
            changed |= transform_expr(body)
        }
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
        // Stable boxed-field lowering introduces bindings such as
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
        Expr::Array(items) | Expr::Tuple(items) => {
            items.iter().map(|i| count_reads_in_expr(i, name)).sum()
        }
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            count_reads_in_expr(l, name) + count_reads_in_expr(r, name)
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => count_reads_in_expr(inner, name),
        Expr::Closure(_, body, _) | Expr::TypedClosure(_, _, body, _) => {
            count_reads_in_expr(body, name)
        }
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
        Expr::Closure(params, body, _) | Expr::TypedClosure(params, _, body, _) => {
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
        Expr::Array(items) | Expr::Tuple(items) => {
            items.iter().map(|i| count_bindings_in_expr(i, name)).sum()
        }
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            count_bindings_in_expr(l, name) + count_bindings_in_expr(r, name)
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
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
        Expr::Array(items) | Expr::Tuple(items) => {
            items.iter_mut().for_each(|i| rename_reads_expr(i, map))
        }
        Expr::BinaryOp(l, _, r) | Expr::Index(l, r) | Expr::Assign(l, r) => {
            rename_reads_expr(l, map);
            rename_reads_expr(r, map);
        }
        Expr::UnaryOp(_, inner)
        | Expr::Parenthesized(inner)
        | Expr::Cast(inner, _)
        | Expr::Reference(inner, _, _)
        | Expr::Await(inner) => rename_reads_expr(inner, map),
        Expr::Closure(params, body, _) | Expr::TypedClosure(params, _, body, _) => {
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

fn ensure_function_comment(function: &mut FunctionDef, comment: &str) {
    if !function.docs.iter().any(|doc| doc.trim() == comment) {
        function.docs.push(comment.to_string());
    }
}

fn closure_param_name(param: &ClosureParam) -> String {
    param.pattern.trim_start_matches("mut ").trim().to_string()
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

#[cfg(test)]
mod tests {
    use super::*;
    use crate::parse_rust_source;

    #[test]
    fn mut_recovery_leaves_last_use_clones_for_the_dedicated_pass() {
        let source = r#"
pub fn update(x0: String) -> String {
    let x = x0.clone();
    let xa = x.clone();
    xa
}
"#;
        let mut module = parse_rust_source(source, "Test").expect("source parses");

        let analysis = optimize_mut(&mut module);

        assert!(analysis.mut_fns.contains("update"));
        let mut generator = RustCodeGenerator::new();
        let printed = generator.generate_module_code(&module);
        assert!(printed.contains("let mut x = x0.clone()"));
        assert!(printed.contains("x = x.clone()"));
    }
}
