theory Sets_Test
  imports Main "Rust.Rust_Setup"
begin

(* Finite sets exercise container code together with equality and tuples. *)

definition nat_set :: "nat set" where
  "nat_set = {1, 2, 3}"

(* Pair elements force tuple equality inside the finite-set representation. *)
definition pair_set :: "(nat \<times> nat) set" where
  "pair_set = {(0, 0), (1, 1)}"

export_code
  nat_set pair_set
  in Rust

end
