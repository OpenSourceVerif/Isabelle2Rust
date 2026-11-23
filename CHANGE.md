# Change History

Major updates and significant bug fixes are recorded here, newest first.

## 2026-11-24 — Stage 1 translation

- Preserve contextual function representations in constructors, mapped
  expressions, function bodies, closures, and case applications.
- Infer mapped argument representations from declared types.
- Resolve class instances from registered metadata and reject incompatible
  implementations mapped to the same Rust type.
- Restore mapped class methods from dictionary metadata.
- Memoize shared dictionary shape reconstruction and type comparisons.
- Indent generated Rust by block structure and print match arm bodies after `=>`.
- Retain Cargo dependency detection for optional Dashu mappings.

## 2026-11-23 — Expression parentheses

- Select parentheses for conditionals, matches, and binding blocks by Rust
  expression position.

## 2026-11-23 — Pattern variable names

- Allocate distinct names across equations and case alternatives in shared
  matches, retaining source names when available.

## 2026-11-22 — Stage-1 numeric profiles

- Add `Rust_Source_BigInt_Setup` with distinct arbitrary-precision Rust types
  for HOL `nat`, `int`, and `integer`.
- Map paired Checked128 division and remainder directly to signed and unsigned
  operations over the full input range.
- Add `Rust_Dashu_Setup` with `dashu_int::UBig` for HOL `nat` and
  `dashu_int::IBig` for `int` and `integer`.

## 2026-10-09 — Shared RustLight parser

- Use the parser in `rustlightast` for Stage-2 parsing.

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
