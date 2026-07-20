theory x64StepRustGenerator
  imports
    Main
    x64Semantics
    "Rust.Rust_Setup"
    "Rust.Rust_U128_Word_Setup"
begin

text \<open>
  This generator exports the same raw single-step semantics definition used by
  the fixed OCaml validation baseline.  In particular, the result remains an
  outcome containing the register and memory maps; observable-state conversion
  is deliberately left to Rust-only test glue outside this stage1 export.
\<close>

text \<open>
  Signed Isabelle word widths use the same phantom width marker as unsigned
  words in the established u128 Rust word setup.  This is a Rust representation
  choice for the raw outcome-producing function, not a wrapper around it.
\<close>

code_printing type_constructor signed \<rightharpoonup>
  (Rust) "crate::Rust'_Word::Signed<_>"

export_code x64_step_test in Rust
  module_name X64_step_test file_prefix x64_step_test

end
