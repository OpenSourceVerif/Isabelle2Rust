# Stage 2 Clippy Warning Backlog

This document records the default Clippy warnings that remain in the generated
Stage 2 unit-test crates after the closure-cast parenthesis cleanup.  It does
not track warnings in the optimizer or RustLightAST implementation crates, and
it does not require Stage 1 output to be Clippy-clean.

## Audited snapshot

- Date: 2026-07-13
- Scope: the 44 manifests matching `test/unit/**/stage2/*/Cargo.toml`
- Regenerated before the audit: `Abstractions_Test`, `Applications_Test`,
  `ArithmeticInt_Test`, `ArithmeticNat_Test`, `BuiltinInstances_Test`,
  `Recursive_Test`, and `Semigroup_Test`
- Command run in each Stage 2 crate:

  ```sh
  RUSTC_BOOTSTRAP=1 cargo clippy --quiet --locked --message-format=short
  ```

The audit reports 9 warnings in four crates.  No generated Stage 2 unit-test
crate currently reports `clippy::double_parens`.

| Crate | Lint | Count | Snapshot locations |
| --- | --- | ---: | --- |
| `ArithmeticInt_Test` | `clippy::useless_vec` | 4 | `src/ArithmeticInt_Test.rs:13,66` |
| `ArithmeticNat_Test` | `clippy::useless_vec` | 1 | `src/Arith.rs:13` |
| `Applications_Test` | `clippy::type_complexity` | 3 | `src/Applications_Test.rs:12,48,80` |
| `Recursive_Test` | `clippy::let_and_return` | 1 | `src/Recursive_Test.rs:22` |

## `clippy::useless_vec`

Stage 1 correctly emits borrowed array literals such as `&[3]`.  During Stage
2 parsing, however, `syn::Expr::Array` is currently lowered to a call whose
callee is the string `vec!`.  The Stage 2 printer therefore changes the source
shape to `&vec!(3)`, which Clippy identifies as a needless allocation.

The durable fix is structural:

1. Add an array-expression node to RustLightAST.
2. Parse `syn::Expr::Array` into that node instead of a synthetic `vec!` call.
3. Print the node as `[e1, ..., en]`.
4. Extend the existing optimizer traversals to recurse into array elements.
5. Add parse/print and `ArithmeticInt_Test`/`ArithmeticNat_Test` regressions.

This is syntax preservation, not a new optimization rule.  Replacing
`&vec!(...)` textually after printing would hide the incorrect AST
representation and should be avoided.

## `clippy::type_complexity`

These warnings describe intentional public function-object types such as
`Rc<dyn Fn(bool, bool) -> (bool, (bool, bool))>`.  They do not indicate an
ownership or semantic defect.

Two possible policies remain to be chosen:

- Introduce generated type aliases and use them consistently in signatures.
  This changes the visible Stage 2 source shape and needs a naming policy.
- Emit a targeted `#[allow(clippy::type_complexity)]` on affected generated
  functions.  This preserves the direct type translation but suppresses a
  style-only lint.

No automatic shortening should be added to an ownership optimization pass.

## `clippy::let_and_return`

The remaining case is a match arm with the block tail shown below:

```rust
let d = d;
d
```

Before adding a new cleanup, audit why the existing identity-let removal in
`match_opt` does not remove this nested match-arm case.  The preferred fix is
to extend that existing traversal or representation-preserving rule and add a
`Recursive_Test` regression.

## Completion criteria

After addressing an entry:

1. Regenerate the affected Stage 1 and Stage 2 crates with `make test`.
2. Build the Stage 2 crate.
3. Run default Clippy with the command above.
4. Re-run the audit over all `test/unit/**/stage2/*/Cargo.toml` manifests.
5. Update the counts and remove resolved entries from this document.
