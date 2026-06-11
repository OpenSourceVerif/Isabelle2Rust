theory Borrow_Move_Demand_Test
  imports Main "Rust.Rust_Setup"
begin

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

export_code mtree_identity mtree_select mtree_make_node mtree_wrap
            mtree_is_leaf mtree_leaf_val
  in Rust

end
