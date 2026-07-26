theory bpf_generator_no_bigint
  imports Main Interpreter rBPFSyntax vm_state rBPFCommType
    "Rust.Rust_Base_Setup"
begin

(* Experimental baseline: retain Isabelle's generated integer/natural-number
   representations instead of selecting the num-bigint adaptations. *)

export_code bpf_interp_test in Rust
  module_name Interp_test file_prefix interp_test

export_code step_test in Rust
  module_name Step_test file_prefix step_test

end
