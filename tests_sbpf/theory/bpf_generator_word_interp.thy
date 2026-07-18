theory bpf_generator_word_interp
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_Setup"
    "Rust.Rust_U128_Word_Setup"
begin

export_code bpf_interp_test in Rust
  module_name Interp_test file_prefix interp_test

end
