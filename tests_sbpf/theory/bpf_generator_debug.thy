theory bpf_generator_debug
  imports Main Interpreter rBPFSyntax vm_state rBPFCommType
  "Rust.Rust_Setup"
begin

export_code step in Rust
  module_name D file_prefix dbg

end
