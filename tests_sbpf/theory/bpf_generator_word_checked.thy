theory bpf_generator_word_checked
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_Checked128_WordU128_Setup"
begin

text \<open>
  SBPF instruction export using the Checked128 numeric profile and the u128
  word layer.
\<close>

code_printing type_constructor signed \<rightharpoonup>
  (Rust) "crate::Rust'_Word::Signed<_>"

export_code step_test in Rust
  module_name Step_test file_prefix step_test

end
