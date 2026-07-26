theory bpf_generator_native
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_Hybrid128_Setup"
begin

text \<open>sBPF instruction export using the hybrid native integer adapter.\<close>

export_code step_test in Rust
  module_name Step_test file_prefix step_test

end
