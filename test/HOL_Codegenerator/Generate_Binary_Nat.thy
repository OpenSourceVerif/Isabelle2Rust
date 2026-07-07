(* Author: Florian Haftmann, TU Muenchen *)

section \<open>Pervasive Rust test of the code generator with binary naturals\<close>

theory Generate_Binary_Nat
imports
  Candidates
  "HOL-Library.AList_Mapping"
  "HOL-Library.Finite_Lattice"
  "HOL-Library.Code_Binary_Nat"
  "Rust.Rust_BigInt_Int_Setup"
begin

text \<open>
  Binary-nat Rust stress-test entry point.  \<^theory>\<open>HOL-Library.Code_Binary_Nat\<close>
  changes the HOL \<^typ>\<open>nat\<close> code representation to zero-or-binary-numeral
  constructors instead of the target-integer mapping used by
  \<^theory>\<open>Rust.Rust_BigInt_Nat_Setup\<close>.  We still import
  \<^theory>\<open>Rust.Rust_BigInt_Int_Setup\<close> because the binary-nat code equations
  and the wider HOL candidate graph use \<^typ>\<open>integer\<close> and \<^typ>\<open>int\<close>, which
  the Rust backend maps to BigInt.
\<close>

export_code _ checking Rust

end
