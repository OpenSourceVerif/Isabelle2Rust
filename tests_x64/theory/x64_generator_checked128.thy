theory x64_generator_checked128
  imports
    Main
    x64Semantics
    "Rust.Rust_Checked128_WordU128_Setup"
begin

text \<open>
  RQ3 performance export of the x86-64 single-step semantics.  Isabelle
  integers and naturals use checked i128/u128 arithmetic, and Isabelle words
  use the native u128 word adapter.
\<close>

code_printing type_constructor signed \<rightharpoonup>
  (Rust) "crate::Rust'_Word::Signed<_>"

export_code x64_step_test in Rust
  module_name X64_step_test file_prefix x64_step_test

end
