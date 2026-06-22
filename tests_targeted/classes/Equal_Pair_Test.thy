theory Equal_Pair_Test
  imports Main "Rust.Rust_Setup"
begin

(* REGRESSION MARKER — currently FAILS `export_code ... in Rust`.

   Bug: `HOL.equal` on a tuple / `prod` crashes the Rust backend.

   Minimal trigger: comparing a pair with `=` forces the code generator to emit
   the `equal :: prod ⇒ prod ⇒ bool` instance (`equal_prod`). But `prod`/`Pair`
   are registered in `Rust_Setup.thy` only as the mixfix templates
   `type_constructor prod ⇀ "( _ , _ )"` and `constant Pair ⇀ "( _ , _ )"`
   (Rust has no nominal Pair constructor / no `impl Equal for (_, _)`), so
   reconstructing the prod equality instance applies a binary mixfix template at
   the wrong arity and the printer raises

       exception Match raised (line 359 of "~~/src/Tools/Code/code_printer.ML")

   (the `fillin` clause of `printer_of_mixfix`).

   Cross-target evidence (proves this is Rust-backend-only, not an Isabelle
   codegen limitation): the SAME definition exports cleanly `in OCaml`,
   `in Haskell` and `in SML`, which all have native structural tuple equality.

   This is the shared root cause behind two fpp Category-A failures:
   * `AVL_Set_Code_Test` — `split_max`/`delete` test `r = Leaf` on a
     `('a × nat) tree`, i.e. equality on a constructor carrying a pair field;
   * `Set_Relation_Test` — `graph1`/`graph2` are `(string × string) set`
     literals, whose finite-set representation needs element (pair) equality
     (see also `types/Set_Pair_Test.thy`).

   Plain pairs are fine (construction, destructuring, partial `Pair`, tuple
   types, tuple-returning functions — see `types/Type_Tuple_Test.thy`); only
   `equal` on a pair triggers the crash. This file flips to PASS once the
   backend reconstructs an `Equal` instance for `prod`. *)

definition eq_pair :: "nat \<times> nat \<Rightarrow> bool" where
  "eq_pair p = (p = (0, 0))"

export_code eq_pair in Rust

end
