theory bpf_generator
  imports Main Interpreter rBPFSyntax vm_state rBPFCommType
  (*"HOL-Library.Code_Target_Numeral"*)
  "Rust.Rust_Setup"
  (*"Go.Go_Setup"*)

begin


(*fun sum_int :: "int list \<Rightarrow> int" where
  "sum_int [] = 0"
| "sum_int (x # xs) = x + sum_int xs"

export_code sum_int in OCaml module_name My_Code
export_code sum_int in Go module_name My_Code*)

code_thms bpf_interp_test

export_code bpf_interp_test in OCaml
  module_name Interp_test file_prefix interp_test

export_code step_test in OCaml
  module_name Step_test file_prefix step_test

(*export_code bpf_interp_test in Go
  module_name Interp_test file_prefix interp_test

export_code step_test in Go
  module_name Step_test file_prefix step_test*)


export_code bpf_interp_test in Rust
  module_name Interp_test file_prefix interp_test

(* export_code  step_test in Rust
  module_name Step_test file_prefix step_test *)


(*
export_code  eval_reg  in OCaml
  module_name Test file_prefix test *)

(*
code_printing type_constructor nat \<rightharpoonup> (OCaml) "nat"
  | constant Nat.Zero_Rep  \<rightharpoonup> (OCaml) "Zero"
  | constant Suc  \<rightharpoonup> (OCaml) "Succ" *)
                                      
(*export_code eval_alu32 in OCaml
  module_name Alu32 file_prefix alu32

export_code eval_neg32 in OCaml
  module_name Neg32 file_prefix neg32

export_code eval_neg64 in OCaml
  module_name Neg64 file_prefix neg64*)

end