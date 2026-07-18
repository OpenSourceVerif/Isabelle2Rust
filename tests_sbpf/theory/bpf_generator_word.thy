theory bpf_generator_word
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_Setup"
    "Rust.Rust_U128_Word_Setup"
begin

text \<open>sBPF export using the u128 word adapter.\<close>

export_code step_test in Rust
  module_name Step_test file_prefix step_test

end
