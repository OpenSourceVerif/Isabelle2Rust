# R-Call Call-Site Redirection — Implementation Todolist

Tracks the work needed to implement rule **R-Call** (`f(ē) ↝ f_copy(ē)`) in
`optimize/src/copy_analysis.rs`.  Steps are linearly dependent — complete them
in order.

---

## Step 1 — Extend `CopyContext` with full function signatures

**File:** `src/copy_analysis.rs`

Add a `FnSig` struct and replace the current `functions: HashMap<String, Type>`
(return type only) with `HashMap<String, FnSig>`.

```rust
struct FnSig {
    params:   Vec<Type>,          // formal parameter types, in order
    generics: Vec<GenericParam>,  // generic params with bounds (Clone / Copy / …)
    ret:      Type,               // return type (previously the only stored field)
}
```

- Update `collect_item` for `Item::Function` to populate `FnSig`.
- Update all existing callers that read `self.functions` (`infer_call_type`,
  `infer_expr_type`) to access `sig.ret` instead of the type directly.
- In `add_copy_specializations`, after emitting each `_copy` specialization,
  **also insert its `FnSig` into `self.functions`** so that step 4 can find it.

> **Why the last point matters:** `add_copy_specializations` currently only
> pushes the new item into `items`; it does not register the `_copy` name in
> `ctx.functions`.  Without this, step 4 cannot discover which `_copy` variants
> exist at call-site rewrite time.

---

## Step 2 — Implement `unify`

**File:** `src/copy_analysis.rs`

```rust
fn unify(
    &self,
    callee: &str,
    actual_types: &[Type],
) -> Option<HashMap<String, Type>>
```

- Look up `callee` in `self.functions`; return `None` if absent.
- Zip `sig.params` with `actual_types`; return `None` if lengths differ.
- For each pair `(formal, actual)`, structurally match:
  - `Type::Named(α)` where `α` is a generic param of `callee` → bind `α → actual`
  - `Type::Generic(name, params)` → recurse into params
  - concrete types → check equality, return `None` on mismatch
- Return `None` if any binding conflicts (same `α` bound to two different types).

---

## Step 3 — Implement the R-Call Copy check

**File:** `src/copy_analysis.rs`

```rust
fn rcall_check(
    &self,
    callee: &str,
    sigma: &HashMap<String, Type>,
    copy_generics: &HashSet<String>,
) -> bool
```

- Look up `CloneBnd(callee)` = generic params of `callee` that have a `Clone`
  bound but **not** a `Copy` bound.
- For each such `α`, compute `sigma.get(α)` (return `false` if absent).
- Check `self.type_is_copy_in_env(sigma(α), copy_generics)`.
- Return `true` iff every such `α` passes.

This reuses the existing `type_is_copy_in_env` — no new Copy logic needed.

---

## Step 4 — Add callee name extraction helper

**File:** `src/copy_analysis.rs`

```rust
fn callee_name<'a>(callee_expr: &'a Expr) -> Option<&'a str>
```

- Match `Expr::Ident(name)` → `Some(name)`.
- Match `Expr::Path(path, PathType::Namespace)` → `Some(path.last())`.
- All other forms → `None` (conservative: leave call unchanged).

To find the `_copy` variant name, look up `name + "_copy"` (and `"_copy2"`,
etc.) in `self.functions`; use the first match that exists.  A small helper:

```rust
fn copy_variant_name(&self, base: &str) -> Option<String>
```

---

## Step 5 — Wire R-Call into `rewrite_expr`

**File:** `src/copy_analysis.rs`, `Expr::Call` arm of `rewrite_expr`

Replace the current pass-through with:

```rust
Expr::Call(callee, args) => {
    self.rewrite_expr(callee, env, copy_generics);
    for arg in args { self.rewrite_expr(arg, env, copy_generics); }

    // R-Call: redirect f(ē) → f_copy(ē) when Copy check passes
    if let Some(name) = callee_name(callee) {
        if let Some(copy_name) = self.copy_variant_name(name) {
            let actual_types: Vec<_> = args.iter()
                .map(|a| self.infer_expr_type(a, env))
                .collect::<Option<_>>()
                .unwrap_or_default();
            if actual_types.len() == args.len() {
                if let Some(sigma) = self.unify(name, &actual_types) {
                    if self.rcall_check(name, &sigma, copy_generics) {
                        // rewrite callee in-place
                        *callee = Box::new(Expr::Ident(copy_name));
                    }
                }
            }
        }
    }
}
```

---

## Step 6 — Add unit tests

**File:** `src/copy_analysis.rs`, `#[cfg(test)]` block

Three cases:

| # | Scenario | Expected |
|---|---|---|
| a | All Clone-bounded params are Copy at call site | call redirected to `_copy` variant |
| b | At least one param is not Copy at call site | call left unchanged |
| c | Nested call inside a `_copy` specialization body | also redirected (step 5 runs inside `rewrite_block` of the specialization) |
