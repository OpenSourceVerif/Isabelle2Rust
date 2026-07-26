theory bpf_generator_word
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_BigInt_WordU128_Setup"
begin

text \<open>sBPF export using the u128 word adapter.\<close>

code_printing type_constructor signed \<rightharpoonup>
  (Rust) "crate::Rust'_Word::Signed<_>"

export_code step_test in Rust
  module_name Step_test file_prefix step_test

end
