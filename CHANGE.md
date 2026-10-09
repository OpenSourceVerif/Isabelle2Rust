# Change History

Major updates and significant bug fixes are recorded here, newest first.

## 2026-10-09 — Shared RustLight parser

- Use the shared `rustlight-parser` crate from RustLightAST for Stage-2 parsing.

## 2026-10-01 — macOS compatibility

- Support the shared Linux/macOS build workflow with portable file locking,
  stack-limit handling, and shell commands.
- Allow configuring the Isabelle executable and additional test sessions.
- Add macOS environment and installation instructions, including OCaml 4.14.2
  for Apple Silicon.

## 2026-09-30 — Rust code generation scope and pattern fixes

- Bind all function parameters simultaneously when destructuring is required,
  preventing source bindings from shadowing pending input parameters.
- Reserve source variable names before eta expansion to avoid collisions with
  generated parameters, including lambda and case-pattern bindings.
- Preserve occupied temporary names across recursive Box pattern matching,
  including pending sibling fields and bindings from other match rows.
- Recognize adapted boolean literals in nested patterns to avoid incorrect
  fallthrough to the non-exhaustive-match fallback.
- Add `Name_Hygiene_Test.thy` with HOL expectations and six embedded Rust
  regression tests covering parameter binding, eta expansion, nested Box
  matching, boolean patterns, and existing scope behavior.
