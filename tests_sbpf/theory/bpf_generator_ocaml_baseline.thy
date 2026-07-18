theory bpf_generator_ocaml_baseline
  imports
    Main Interpreter rBPFSyntax vm_state rBPFCommType
    "HOL-Library.Code_Target_Int"
    "HOL-Library.Code_Target_Nat"
begin

text \<open>
  Stable OCaml baseline.  In particular, this theory does not import the Rust
  direct-shift setup, so its generated arithmetic remains identical to the
  original sBPF OCaml comparison.
\<close>

export_code bpf_interp_test in OCaml
  module_name Interp_test file_prefix interp_test

export_code step_test in OCaml
  module_name Step_test file_prefix step_test

end
