theory bpf_generator_native_interp
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_Hybrid128_Setup"
begin

text \<open>sBPF interpreter export using the hybrid native integer adapter.\<close>

export_code bpf_interp_test in Rust
  module_name Interp_test file_prefix interp_test

end
