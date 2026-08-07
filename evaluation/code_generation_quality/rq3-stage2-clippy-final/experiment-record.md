# Final RQ3 Stage-2 Clippy record

- Scope: tracked generated Stage-2 crates only. Stage-1 was not executed.
- Corpus: 92 crates, comprising 1 HOL, 55 Unit, and 36 FPP crates.
- Toolchain: clippy 0.1.94 (4a4ef493e3 2026-03-02).
- Result: 16 diagnostics and 0 failed Clippy commands.
- Untracked theories under `test/unit/example` are outside the frozen corpus.
- Each crate hash covers `Cargo.toml`, `Cargo.lock`, and non-target Rust source files using length-delimited relative paths and contents.

## Residual diagnostics

| Diagnostic | Count |
| --- | ---: |
| `clippy::overly_complex_bool_expr` | 1 |
| `clippy::too_many_arguments` | 2 |
| `clippy::type_complexity` | 4 |
| `unconditional_recursion` | 9 |
| **Total** | **16** |
