theory Set_Pair_Test
  imports Main "Rust.Rust_Setup"
begin

(* REGRESSION MARKER — currently FAILS `export_code ... in Rust`.

   Bug: a finite *set of pairs* cannot be exported to Rust. This is the
   set-literal manifestation of the tuple-equality crash documented in
   `classes/Equal_Pair_Test.thy`: a finite-set representation deduplicates via
   element equality, so `{(0,0),(1,1)} :: (nat × nat) set` forces `HOL.equal`
   on `prod`. Because `prod`/`Pair` are only mixfix templates `( _ , _ )` in
   `Rust_Setup.thy` (no `impl Equal for (_, _)`), reconstructing prod equality
   applies a binary template at the wrong arity:

       exception Match raised (line 359 of "~~/src/Tools/Code/code_printer.ML")

   Cross-target evidence (Rust-backend-only): the same `g` exports cleanly
   `in OCaml`, `in Haskell` and `in SML`.

   Contrast — these already PASS in Rust, so the trigger is specifically the
   *pair* element, not sets in general:
   * `nat set`    : `{1,2,3}`
   * `string set` : `{''v1'',''v2''}`  (char-list elements)

   This is the fpp `Set_Relation_Test` failure (`graph1`/`graph2` are
   `(string × string) set`). Flips to PASS once the backend can print an
   `Equal` instance for `prod`. *)

definition g :: "(nat \<times> nat) set" where
  "g = {(0, 0), (1, 1)}"

export_code g in Rust

end
