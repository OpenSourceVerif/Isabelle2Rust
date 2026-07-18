theory bpf_generator_word_native_interp
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_Setup"
    "Rust.Rust_U128_Word_Native_Setup"
begin

text \<open>
  sBPF interpreter export combining the u128 word adapter with the hybrid
  native integer adapter.
\<close>

code_printing type_constructor signed \<rightharpoonup>
  (Rust) "crate::Rust'_Word::Signed<_>"

export_code bpf_interp_test in Rust
  module_name Interp_test file_prefix interp_test

end
