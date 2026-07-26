theory Set_Pair_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* REGRESSION — finite *set of pairs* (now FIXED, exports + compiles).

   This is the set-literal manifestation of the tuple-equality reconstruction
   documented in `classes/Equal_Pair_Test.thy`: a finite-set representation
   deduplicates via element equality, so `{(0,0),(1,1)} :: (nat × nat) set`
   forces `HOL.equal` on `prod`. The backend now reconstructs
   `impl<A: Equal, B: Equal> Equal for (A, B)` and dispatches tuple-equality
   calls as `<(A, B) as Equal>::equal(..)`; see `classes/Equal_Pair_Test.thy`
   for the `code_rust.ML` fix.

   The `nat set` (`{1,2,3}`) and `string set` (`{''v1'',''v2''}`) probes
   already passed; this file adds the *pair* element case. Same fix unblocks the
   fpp `Set_Relation_Test` (`graph1`/`graph2` are `(string × string) set`). *)

definition g :: "(nat \<times> nat) set" where
  "g = {(0, 0), (1, 1)}"

export_code g in Rust

end
