theory bpf_generator_bigint
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_BigInt_Setup"
begin

text \<open>
  RQ2 export profile.  Isabelle integers, ints, and naturals use the
  arbitrary-precision Rust BigInt setup.  The OCaml exports provide the shared
  reference implementation for both sBPF evaluation profiles.
\<close>

export_code bpf_interp_test in OCaml
  module_name Interp_test file_prefix interp_test

export_code step_test in OCaml
  module_name Step_test file_prefix step_test

export_code bpf_interp_test in Rust
  module_name Interp_test file_prefix interp_test

export_code step_test in Rust
  module_name Step_test file_prefix step_test

end
