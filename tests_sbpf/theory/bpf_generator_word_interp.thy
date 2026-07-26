theory bpf_generator_word_interp
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_BigInt_WordU128_Setup"
begin

code_printing type_constructor signed \<rightharpoonup>
  (Rust) "crate::Rust'_Word::Signed<_>"

export_code bpf_interp_test in Rust
  module_name Interp_test file_prefix interp_test

end
