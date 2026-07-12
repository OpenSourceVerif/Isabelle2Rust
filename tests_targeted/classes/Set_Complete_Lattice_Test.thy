theory Set_Complete_Lattice_Test
  imports Main "Rust.Rust_Setup"
begin

(* hol-stress guidance test (Generate.thy: Complete_Lattices.rs,
   Lattice_Constructions.rs and Order_Continuity.rs -- E0599/E0034).

   A set participates in both the binary lattice class (`sup`) and the complete
   lattice class (`Sup`).  Reconstructed Rust impl bodies must dispatch the
   empty complete union to the set's `Bot` implementation and must distinguish
   the two generated traits whose base method name is `sup`.

   In the broad crate the backend emits unresolved `Set::bot()` / `Set::sup()`
   associated calls, and generic code that mentions both traits emits the
   ambiguous `A::sup(...)`.  The first wrapper exercises the Set complete-lattice
   instance; the second deliberately keeps binary and complete suprema together
   so trait qualification is required. *)

definition complete_set_union :: "'a set set \<Rightarrow> 'a set" where
  "complete_set_union A = Sup A"

definition binary_after_complete_sup :: "'a::complete_lattice set \<Rightarrow> 'a \<Rightarrow> 'a" where
  "binary_after_complete_sup A x = sup (Sup A) x"

export_code complete_set_union binary_after_complete_sup in Rust

end
