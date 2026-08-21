theory x64_generator_bigint
  imports
    Main
    x64Assembler
    x64Semantics
    "Rust.Rust_BigInt_WordU128_Setup"
begin

text \<open>
  RQ2 Rust exports.  Isabelle integers and naturals use BigInt, while Isabelle
  words use the native u128 word adapter.  Parsing and correctness observation
  remain external harness responsibilities.
\<close>

code_printing type_constructor signed \<rightharpoonup>
  (Rust) "crate::Rust'_Word::Signed<_>"

export_code x64_encode in Rust
  module_name X64_encode file_prefix x64_encode

export_code x64_step_test in Rust
  module_name X64_step_test file_prefix x64_step_test

end
