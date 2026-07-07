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

  DEBUG SCAFFOLD (Phase A): while stabilising the broad export we use
  \<^text>\<open>in Rust\<close> so the generated crate is persisted via the
  session's \<^text>\<open>export_files\<close> and can be inspected / \<^text>\<open>cargo build\<close>ed
  outside Isabelle.  Once the crate compiles cleanly this reverts to
  \<^theory_text>\<open>export_code _ checking Rust\<close> to match the other language backends.
\<close>

export_code _ in Rust

end
