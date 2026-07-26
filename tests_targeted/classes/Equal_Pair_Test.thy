theory Equal_Pair_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* REGRESSION — `HOL.equal` on a tuple / `prod` (now FIXED, exports + compiles).

   Trigger: comparing a pair with `=` forces the code generator to emit the
   `equal :: prod ⇒ prod ⇒ bool` instance (`equal_prod`). `prod`/`Pair` are
   registered in `Rust_Base_Setup.thy` only as the mixfix templates
   `type_constructor prod ⇀ "( _ , _ )"` and `constant Pair ⇀ "( _ , _ )"`
   (Rust has no nominal Pair constructor), so the instance must be reconstructed
   as `impl<A: Equal, B: Equal> Equal for (A, B)`.

   The fix is in `code_rust.ML`:
   * `canon_tyco` now feeds the tuple mixfix template placeholder args matching
     its arity (it formerly passed `[]`, crashing `printer_of_mixfix`);
   * an instance-method call whose receiver type is mixfix-mapped (a tuple) is
     dispatched through Rust's fully qualified form
     `<(A, B) as Equal>::equal(..)` instead of the inexpressible `Tyco::equal`.

   The reconstructed `impl Equal for (A, B)` recurses through the element
   `Equal` bounds, exactly mirroring the native structural tuple equality the
   OCaml/Haskell/SML backends rely on.

   Same root cause behind the fpp `AVL_Set_Code_Test` and `Set_Relation_Test`
   (`(string × string) set`) failures; see also `types/Set_Pair_Test.thy`. *)

definition eq_pair :: "nat \<times> nat \<Rightarrow> bool" where
  "eq_pair p = (p = (0, 0))"

export_code eq_pair in Rust

end
