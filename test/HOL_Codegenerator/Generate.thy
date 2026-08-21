(* Author: Florian Haftmann, TU Muenchen *)

section \<open>Pervasive Rust test of the code generator\<close>

theory Generate
imports
  Candidates
  "HOL-Library.AList_Mapping"
  "HOL-Library.Finite_Lattice"
  "Rust.Rust_BigInt_Setup"
begin

text \<open>
  Standard Rust stress-test entry point.  The wildcard export asks Isabelle to
  generate every reachable code equation from the imported candidate theories;
  \<^theory>\<open>Rust.Rust_BigInt_Setup\<close> maps HOL \<^typ>\<open>integer\<close>, \<^typ>\<open>int\<close>
  and \<^typ>\<open>nat\<close> to Rust BigInt operations.

  The session exports the complete generated crate to the persistent Stage-1
  experiment directory, where the stress target checks it with Cargo.
\<close>

export_code _ in Rust

end
