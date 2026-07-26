theory bpf_generator_default_step
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_BigInt_Setup"
begin

export_code step_test in Rust
  module_name Step_test file_prefix step_test

end
