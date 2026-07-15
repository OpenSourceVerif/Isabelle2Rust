theory BorrowCalls_Test
  imports Main "Rust.Rust_Setup"
begin

(* Recursive calls should reuse borrowed parameters while rebuilding results. *)

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

(* Multi-argument calls exercise borrowability per parameter. *)

datatype mp_tree =
    MPLeaf bool
  | MPNode mp_tree mp_tree

fun mp_pair_return :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> mp_tree \<times> mp_tree" where
  "mp_pair_return t u = (t, u)"

fun mp_check_or_return :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> mp_tree" where
  "mp_check_or_return (MPLeaf _) u = u"
| "mp_check_or_return (MPNode _ _) u = u"

fun mp_compare :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> bool" where
  "mp_compare (MPLeaf b1) (MPLeaf b2) = (b1 = b2)"
| "mp_compare (MPLeaf _) (MPNode _ _) = False"
| "mp_compare (MPNode _ _) (MPLeaf _) = False"
| "mp_compare (MPNode _ _) (MPNode _ _) = True"

fun mp_build_and_check :: "mp_tree \<Rightarrow> mp_tree \<Rightarrow> bool" where
  "mp_build_and_check _ (MPLeaf b) = b"
| "mp_build_and_check _ (MPNode _ _) = False"

fun mp_flag_and_observe :: "bool \<Rightarrow> mp_tree \<Rightarrow> bool" where
  "mp_flag_and_observe flag (MPLeaf b) = (flag \<and> b)"
| "mp_flag_and_observe flag (MPNode _ _) = flag"

(* Recursive and generic values exercise call-summary propagation. *)

datatype borrow_tree =
    BLeaf bool
  | BNode borrow_tree borrow_tree

fun btree_is_leaf :: "borrow_tree \<Rightarrow> bool" where
  "btree_is_leaf (BLeaf _) = True"
| "btree_is_leaf (BNode _ _) = False"

fun btree_leaf_val :: "borrow_tree \<Rightarrow> bool" where
  "btree_leaf_val (BLeaf b) = b"
| "btree_leaf_val (BNode _ _) = False"

fun btree_dup :: "borrow_tree \<Rightarrow> borrow_tree \<times> borrow_tree" where
  "btree_dup x = (x, x)"

datatype 'a borrow_box =
  BorrowBox 'a

fun bbox_get :: "'a borrow_box \<Rightarrow> 'a" where
  "bbox_get (BorrowBox x) = x"

fun bbox_dup :: "'a borrow_box \<Rightarrow> 'a borrow_box \<times> 'a borrow_box" where
  "bbox_dup x = (x, x)"

fun bbox_swap ::
  "'a borrow_box \<Rightarrow> 'a borrow_box \<Rightarrow> 'a borrow_box \<times> 'a borrow_box" where
  "bbox_swap x y = (y, x)"

export_code
  any_label any_label_twice rebuild mp_pair_return mp_check_or_return mp_compare
  mp_build_and_check mp_flag_and_observe btree_is_leaf btree_leaf_val btree_dup
  bbox_get bbox_dup bbox_swap
  in Rust

end
