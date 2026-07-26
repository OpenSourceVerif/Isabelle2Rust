theory bpf_generator_word_checked_interp
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_Checked128_WordU128_Setup"
begin

text \<open>
  SBPF interpreter export using the Checked128 numeric profile and the u128
  word layer.
\<close>

code_printing type_constructor signed \<rightharpoonup>
  (Rust) "crate::Rust'_Word::Signed<_>"

export_code bpf_interp_test in Rust
  module_name Interp_test file_prefix interp_test

end
