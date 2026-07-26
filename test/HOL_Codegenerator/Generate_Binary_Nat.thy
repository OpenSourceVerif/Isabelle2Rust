(* Author: Florian Haftmann, TU Muenchen *)

section \<open>Pervasive Rust test of the code generator with binary naturals\<close>

theory Generate_Binary_Nat
imports
  Candidates
  "HOL-Library.AList_Mapping"
  "HOL-Library.Finite_Lattice"
  "HOL-Library.Code_Binary_Nat"
  "Rust.Rust_Integer_BigInt_Layer"
begin

text \<open>
  Binary-nat Rust stress-test entry point.  \<^theory>\<open>HOL-Library.Code_Binary_Nat\<close>
  changes the HOL \<^typ>\<open>nat\<close> code representation to zero-or-binary-numeral
  constructors instead of the target-integer mapping used by
  \<^text>\<open>Rust_BigInt_Setup\<close>.  The latter theory is deliberately not an
  ancestor here because its target-integer representation conflicts with the
  binary-numeral representation under test.  We still import
  \<^theory>\<open>Rust.Rust_Integer_BigInt_Layer\<close> because the binary-nat code equations
  and the wider HOL candidate graph use \<^typ>\<open>integer\<close> and \<^typ>\<open>int\<close>, which
  the Rust backend maps to BigInt.

  The session exports this binary-nat variant of the complete generated crate
  to the persistent Stage-1 experiment directory, where the stress target
  checks it with Cargo.
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
    writeln ("HOL_STRESS_STATS theory=Generate_Binary_Nat entry_points=" ^
      string_of_int (length constants) ^ " definitions=" ^
      string_of_int definitions)
  end
\<close>

export_code _ in Rust

end
