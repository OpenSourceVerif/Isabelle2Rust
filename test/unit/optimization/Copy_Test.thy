theory Copy_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Copy_Bool_Fields_Test"


datatype flag_pair =
  FlagPair bool bool

fun get_left :: "flag_pair \<Rightarrow> bool" where
  "get_left (FlagPair x y) = x"

fun get_right :: "flag_pair \<Rightarrow> bool" where
  "get_right (FlagPair x y) = y"

fun swap_flag_pair :: "flag_pair \<Rightarrow> flag_pair" where
  "swap_flag_pair (FlagPair x y) = FlagPair y x"

subsection "From Copy_Generic_Bound_Test"


datatype 'a copy_wrap =
  CopyWrap 'a

fun duplicate :: "'a \<Rightarrow> 'a \<times> 'a" where
  "duplicate x = (x, x)"

fun duplicate_wrap :: "'a copy_wrap \<Rightarrow> 'a copy_wrap \<times> 'a copy_wrap" where
  "duplicate_wrap x = (x, x)"

subsection "From Copy_Nat_NonCopy_Test"


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

subsection "From Copy_Nested_Types_Test"


datatype color =
    Red
  | Green
  | Blue

fun is_red :: "color \<Rightarrow> bool" where
  "is_red Red = True"
| "is_red Green = False"
| "is_red Blue = False"

datatype pixel =
  Pixel color color color

fun get_first_color :: "pixel \<Rightarrow> color" where
  "get_first_color (Pixel r g b) = r"

fun rotate_pixel :: "pixel \<Rightarrow> pixel" where
  "rotate_pixel (Pixel r g b) = Pixel g b r"


fun replace_first_color :: "pixel \<Rightarrow> color \<Rightarrow> pixel" where
  "replace_first_color (Pixel r g b) c = Pixel c g b"

subsection "From Copy_Recursive_NonCopy_Test"


(* ── Unit test: non-Copy fields stop Copy propagation upward ─────────────────
   copy_tree is recursive (BNode stores Box<CopyTree>) → non-Copy.
   Any type that contains copy_tree as a field is also non-Copy, even if all
   other fields are bool (Copy).  The copy pass must not infer Copy for such
   compound types.

   At the same time, types that only contain Copy fields (bool, other Copy
   user-defined types) SHOULD be promoted to Copy.                            *)

(* Recursive → non-Copy regardless of field types *)
datatype small_tree =
    SLeaf bool
  | SNode small_tree small_tree

(* Wraps a non-Copy tree → must stay non-Copy *)
datatype tree_holder =
  TreeHolder small_tree bool

(* Wraps only bool fields → SHOULD become Copy *)
datatype flag_holder =
  FlagHolder bool bool

(* Generic wrapper: Copy only when 'a is Copy *)
datatype 'a opt_val =
    OptNone
  | OptSome 'a

(* flag_holder is Copy → opt_val<flag_holder> SHOULD be Copy *)
(* small_tree is non-Copy → opt_val<small_tree> must stay non-Copy *)

fun stree_is_leaf :: "small_tree \<Rightarrow> bool" where
  "stree_is_leaf (SLeaf _) = True"
| "stree_is_leaf (SNode _ _) = False"

fun stree_dup :: "small_tree \<Rightarrow> small_tree \<times> small_tree" where
  "stree_dup x = (x, x)"

fun holder_flag :: "tree_holder \<Rightarrow> bool" where
  "holder_flag (TreeHolder _ b) = b"

fun holder_dup :: "tree_holder \<Rightarrow> tree_holder \<times> tree_holder" where
  "holder_dup x = (x, x)"

fun flag_holder_dup :: "flag_holder \<Rightarrow> flag_holder \<times> flag_holder" where
  "flag_holder_dup x = (x, x)"

fun opt_val_has :: "'a opt_val \<Rightarrow> bool" where
  "opt_val_has OptNone = False"
| "opt_val_has (OptSome _) = True"

fun opt_val_dup :: "'a opt_val \<Rightarrow> 'a opt_val \<times> 'a opt_val" where
  "opt_val_dup x = (x, x)"

fun flag_holder_opt_dup :: "flag_holder opt_val \<Rightarrow> flag_holder opt_val \<times> flag_holder opt_val" where
  "flag_holder_opt_dup x = opt_val_dup x"

export_code
  get_left get_right swap_flag_pair duplicate duplicate_wrap count_box_val count_box_dup
  count_pair_fst count_pair_dup mixed_flag mixed_dup bool_triple_first bool_triple_dup
  bool_triple_rotate is_red get_first_color rotate_pixel replace_first_color
  stree_is_leaf stree_dup holder_flag holder_dup flag_holder_dup opt_val_has opt_val_dup
  flag_holder_opt_dup
  in Rust

end
