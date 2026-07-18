(* Author: Florian Haftmann, TU Muenchen *)

section \<open>Pervasive Rust test of the code generator\<close>

theory Generate
imports
  Candidates
  "HOL-Library.AList_Mapping"
  "HOL-Library.Finite_Lattice"
  "Rust.Rust_BigInt_Nat_Setup"
begin

text \<open>
  Standard Rust stress-test entry point.  The wildcard export asks Isabelle to
  generate every reachable code equation from the imported candidate theories;
  \<^theory>\<open>Rust.Rust_BigInt_Nat_Setup\<close> maps HOL \<^typ>\<open>integer\<close>, \<^typ>\<open>int\<close>
  and \<^typ>\<open>nat\<close> to Rust BigInt operations.

  The session exports the complete generated crate to the persistent Stage-1
  experiment directory, where the stress target checks it with Cargo.
\<close>

ML_val \<open>
  let
    val constants = Code_Thingol.read_const_exprs @{context} ["_"];
    val program = Code_Thingol.consts_program @{context} constants;
    val definitions =
      Code_Symbol.Graph.dest program
      |> filter (fn ((_, Code_Thingol.Fun _), _) => true | _ => false)
      |> length;
  in
    writeln ("HOL_STRESS_STATS theory=Generate entry_points=" ^
      string_of_int (length constants) ^ " definitions=" ^
      string_of_int definitions)
  end
\<close>

export_code _ in Rust

end
