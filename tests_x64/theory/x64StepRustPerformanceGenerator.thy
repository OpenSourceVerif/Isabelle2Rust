theory x64StepRustPerformanceGenerator
  imports
    Main
    x64Semantics
    "Rust.Rust_Checked128_WordU128_Setup"
begin

text \<open>
  Performance export of the x86-64 single-step semantics.  It keeps the HOL
  entry point unchanged while selecting the same Word plus Checked128
  Int/Nat representation used by the SBPF RQ3 experiment.  Parsing,
  observation, correctness comparison, and metric collection remain external
  harness responsibilities.
\<close>

code_printing type_constructor signed \<rightharpoonup>
  (Rust) "crate::Rust'_Word::Signed<_>"

export_code x64_step_test in Rust
  module_name X64_step_test file_prefix x64_step_test

end
