theory Borrow_Test
  imports Main "Rust.Rust_Setup"
begin

subsection "From Borrow_CopyField_Own_Test"


(* ── Unit test: extracting Copy-typed fields does not block borrow inference ──
   When a non-Copy parameter is matched and a Copy-typed field is used in an
   owned position (e.g., returned or put in a constructor), the borrow pass
   classifies this as  Own(CopyUse)  – a demand that is compatible with shared
   borrowing (the value can be copied from a & reference).

   This contrasts with using a non-Copy field without .clone() (Move demand).

   After the copy pass, fields of Copy types (bool, user-defined Copy enums)
   are known to be Copy, so the borrow pass can apply the  Own(CopyUse) rule.  *)

(* Recursive tree: non-Copy.  Leaf carries a bool (Copy) label.              *)
datatype ce_tree =
    CELeaf bool
  | CENode ce_tree ce_tree

(* Wrapper holding a bool (Copy) and a ce_tree (non-Copy).                   *)
datatype ce_holder =
  CEHolder bool ce_tree

(* Returns a Copy bool field extracted from the non-Copy tree.
   In the baseline: `b.clone()`.  Copy-field use → Own(CopyUse) → borrowable. *)
fun ce_leaf_val :: "ce_tree \<Rightarrow> bool" where
  "ce_leaf_val (CELeaf b) = b"
| "ce_leaf_val (CENode _ _) = False"

(* Returns the bool (Copy) flag from the holder.
   The ce_tree sub-field is never touched → Obs on the holder param overall.  *)
fun ce_holder_flag :: "ce_holder \<Rightarrow> bool" where
  "ce_holder_flag (CEHolder b _) = b"

(* Uses the bool field in a new bool expression (still Copy use) → borrowable *)
fun ce_leaf_negated :: "ce_tree \<Rightarrow> bool" where
  "ce_leaf_negated (CELeaf b) = (\<not> b)"
| "ce_leaf_negated (CENode _ _) = True"

(* Observational depth-check: returns bool, never moves tree → borrowable *)
fun ce_is_single_leaf :: "ce_tree \<Rightarrow> bool" where
  "ce_is_single_leaf (CELeaf _) = True"
| "ce_is_single_leaf (CENode (CELeaf _) (CELeaf _)) = True"
| "ce_is_single_leaf _ = False"

subsection "From Borrow_Move_Demand_Test"


(* ── Unit test: functions with Move demand must NOT get borrow variants ───────
   The borrow pass emits a  f_borrow  variant only when the demand set on every
   borrowable parameter is  ⊆ {Obs, Bor, Own}  and every Own demand comes from
   an explicit .clone() or a Copy use.

   Functions here deliberately impose a Move demand (Demand::Move) by either:
     (a) directly returning the non-Copy parameter in tail position, or
     (b) passing the non-Copy parameter to an ownership-consuming call without
         an intervening .clone().

   None of these functions should have a  _borrow  variant in stage2.         *)

datatype move_tree =
    MLeaf bool
  | MNode move_tree move_tree

(* ── Case (a): direct return of non-Copy parameter → Move demand ─────────── *)

(* identity: returns the tree unchanged – the param is in tail/return position
   with a non-Copy type, so demand is Move.                                    *)
fun mtree_identity :: "move_tree \<Rightarrow> move_tree" where
  "mtree_identity t = t"

(* select_child: returns one of two non-Copy sub-trees directly.
   Both l and r are in return position in different branches → Move on both.  *)
fun mtree_select :: "bool \<Rightarrow> move_tree \<Rightarrow> move_tree \<Rightarrow> move_tree" where
  "mtree_select True  l _ = l"
| "mtree_select False _ r = r"

(* ── Case (b): pass parameter into constructor without clone → Move demand ── *)

(* make_node: builds a new BNode with both sub-trees taken by value.
   l and r are owned-position constructor args without .clone() → Move.       *)
fun mtree_make_node :: "move_tree \<Rightarrow> move_tree \<Rightarrow> move_tree" where
  "mtree_make_node l r = MNode l r"

(* wrap_leaf: wraps an existing tree inside a unary node (with a dummy leaf).
   The tree argument is consumed as-is → Move demand.                         *)
fun mtree_wrap :: "move_tree \<Rightarrow> move_tree" where
  "mtree_wrap t = MNode (MLeaf True) t"

(* ── For contrast: observational functions ARE borrowable ─────────────────── *)

fun mtree_is_leaf :: "move_tree \<Rightarrow> bool" where
  "mtree_is_leaf (MLeaf _) = True"
| "mtree_is_leaf (MNode _ _) = False"

fun mtree_leaf_val :: "move_tree \<Rightarrow> bool" where
  "mtree_leaf_val (MLeaf b) = b"
| "mtree_leaf_val (MNode _ _) = False"

subsection "From Borrow_Paper_Example_Test"


datatype tree =
    Leaf bool
  | Branch tree tree

fun any_label :: "tree \<Rightarrow> bool" where
  "any_label (Leaf b) = b"
| "any_label (Branch l r) = (any_label l \<or> any_label r)"

definition any_label_twice :: "tree \<Rightarrow> bool" where
  "any_label_twice t = (any_label t \<and> any_label t)"

fun rebuild :: "tree \<Rightarrow> tree" where
  "rebuild (Leaf b) = Leaf b"
| "rebuild (Branch l r) = Branch (rebuild l) (rebuild r)"

subsection "From Borrow_Per_Param_Test"


(* ── Unit test: per-parameter borrowability in multi-argument functions ───────
   The borrow pass analyses each parameter independently.  A function with
   mixed demands across its parameters should get a  _borrow  variant where
   only the borrowable positions are changed to  &T.

   Scenarios here:
     • one param observed-only, another returned directly (Move) → first
       position is borrowable, second is not
     • two params both observed → both borrowable
     • one param moved into a constructor, other param observed → second
       borrowable, first not
     • bool param (Copy) is never a borrow candidate (already cheap to pass)  *)

datatype mp_tree =
    MPLeaf bool
  | MPNode mp_tree mp_tree

(* both params are returned directly (Move) → neither is borrowable *)
fun mp_pair_return :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> mp_tree \<times> mp_tree" where
  "mp_pair_return t u = (t, u)"

(* first param observed (→ borrowable), second returned directly (Move → not) *)
fun mp_check_or_return :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> mp_tree" where
  "mp_check_or_return (MPLeaf _) u = u"
| "mp_check_or_return (MPNode _ _) u = u"

(* both params observed → both borrowable *)
fun mp_compare :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> bool" where
  "mp_compare (MPLeaf b1) (MPLeaf b2) = (b1 = b2)"
| "mp_compare (MPLeaf _) (MPNode _ _) = False"
| "mp_compare (MPNode _ _) (MPLeaf _) = False"
| "mp_compare (MPNode _ _) (MPNode _ _) = True"

(* first param consumed into constructor (Move → not borrowable),
   second param only observed (→ borrowable) *)
fun mp_build_and_check :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> bool" where
  "mp_build_and_check t (MPLeaf b) = b"
| "mp_build_and_check t (MPNode _ _) = False"

(* bool param (Copy) is not a borrow candidate; mp_tree param is observed *)
fun mp_flag_and_observe :: "bool \<Rightarrow> mp_tree \<Rightarrow> bool" where
  "mp_flag_and_observe flag (MPLeaf b) = (flag \<and> b)"
| "mp_flag_and_observe flag (MPNode _ _) = flag"

subsection "From Borrow_Tree_Generic_Test"


(* ── Recursive non-Copy tree type ───────────────────────────────────────────
   BorrowTree stays non-Copy after the copy pass because it is recursive
   (the BNode constructor stores Box<BorrowTree> fields).  This makes it a
   good carrier for testing borrow inference on non-trivial types.          *)

datatype borrow_tree =
    BLeaf bool
  | BNode borrow_tree borrow_tree

(* observe-only: inspect the top constructor, return Copy bool → borrowable *)
fun btree_is_leaf :: "borrow_tree \<Rightarrow> bool" where
  "btree_is_leaf (BLeaf _) = True"
| "btree_is_leaf (BNode _ _) = False"

(* observe: extract Copy value from a leaf → borrowable *)
fun btree_leaf_val :: "borrow_tree \<Rightarrow> bool" where
  "btree_leaf_val (BLeaf b) = b"
| "btree_leaf_val (BNode _ _) = False"

(* dup: Isabelle generates two clone calls (multi-use) → both Own demands
   → borrowable even though BorrowTree is non-Copy                          *)
fun btree_dup :: "borrow_tree \<Rightarrow> borrow_tree \<times> borrow_tree" where
  "btree_dup x = (x, x)"

(* ── Generic non-Copy wrapper ──────────────────────────────────────────────
   borrow_box<A> is non-Copy when A is not Copy.  These functions test that
   borrow inference is emitted correctly for generic Clone-bounded params.  *)

datatype 'a borrow_box =
    BorrowBox 'a

(* get inner value: single use via clone → borrowable *)
fun bbox_get :: "'a borrow_box \<Rightarrow> 'a" where
  "bbox_get (BorrowBox x) = x"

(* dup generic box: two clone uses → borrowable *)
fun bbox_dup :: "'a borrow_box \<Rightarrow> 'a borrow_box \<times> 'a borrow_box" where
  "bbox_dup x = (x, x)"

(* swap inside a pair of boxes: both inputs cloned → both borrowable *)
fun bbox_swap :: "'a borrow_box \<Rightarrow> 'a borrow_box \<Rightarrow> 'a borrow_box \<times> 'a borrow_box" where
  "bbox_swap x y = (y, x)"

export_code
  ce_leaf_val ce_holder_flag ce_leaf_negated ce_is_single_leaf mtree_identity
  mtree_select mtree_make_node mtree_wrap mtree_is_leaf mtree_leaf_val any_label
  any_label_twice rebuild mp_pair_return mp_check_or_return mp_compare
  mp_build_and_check mp_flag_and_observe btree_is_leaf btree_leaf_val btree_dup bbox_get
  bbox_dup bbox_swap
  in Rust

end
