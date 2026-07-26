theory Copy_Nat_NonCopy_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* ── Unit test: nat fields block Copy inference ──────────────────────────────
   Isabelle's nat translates to a recursive enum  Nat = ZeroNat | Suc(Box<Nat>)
   which cannot implement Copy.  Any datatype wrapping nat must therefore stay
   Clone-only after the copy pass.  Functions that use such values must still
   emit .clone() calls.

   This is contrasted with a purely-bool type that SHOULD derive Copy.        *)

datatype count_box =
  CountBox nat

datatype count_pair =
  CountPair nat nat

(* Mixed: bool field is Copy but nat field is not → whole type stays Clone-only *)
datatype mixed_count =
  MixedCount bool nat

(* Purely-bool type for contrast: SHOULD derive Copy after the pass *)
datatype bool_triple =
  BoolTriple bool bool bool

fun count_box_val :: "count_box \<Rightarrow> nat" where
  "count_box_val (CountBox n) = n"

(* Dup forces two uses → clone retained because CountBox is non-Copy *)
fun count_box_dup :: "count_box \<Rightarrow> count_box \<times> count_box" where
  "count_box_dup x = (x, x)"

fun count_pair_fst :: "count_pair \<Rightarrow> nat" where
  "count_pair_fst (CountPair x _) = x"

(* Dup of non-Copy pair: clone retained *)
fun count_pair_dup :: "count_pair \<Rightarrow> count_pair \<times> count_pair" where
  "count_pair_dup p = (p, p)"

fun mixed_flag :: "mixed_count \<Rightarrow> bool" where
  "mixed_flag (MixedCount b _) = b"

(* Dup of mixed type: clone retained because nat field blocks Copy *)
fun mixed_dup :: "mixed_count \<Rightarrow> mixed_count \<times> mixed_count" where
  "mixed_dup x = (x, x)"

(* Contrast: purely-bool type → Copy inferred, dup should eliminate clones *)
fun bool_triple_first :: "bool_triple \<Rightarrow> bool" where
  "bool_triple_first (BoolTriple x _ _) = x"

fun bool_triple_dup :: "bool_triple \<Rightarrow> bool_triple \<times> bool_triple" where
  "bool_triple_dup x = (x, x)"

fun bool_triple_rotate :: "bool_triple \<Rightarrow> bool_triple" where
  "bool_triple_rotate (BoolTriple x y z) = BoolTriple y z x"

export_code count_box_val count_box_dup
            count_pair_fst count_pair_dup
            mixed_flag mixed_dup
            bool_triple_first bool_triple_dup bool_triple_rotate
  in Rust

end
