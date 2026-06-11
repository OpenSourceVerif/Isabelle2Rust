theory Borrow_Tree_Generic_Test
  imports Main "Rust.Rust_Setup"
begin

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

export_code btree_is_leaf btree_leaf_val btree_dup
            bbox_get bbox_dup bbox_swap
  in Rust

end
