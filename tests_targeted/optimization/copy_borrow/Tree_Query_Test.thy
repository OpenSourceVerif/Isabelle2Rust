theory Tree_Query_Test
  imports Main "Rust.Rust_Setup"
begin

(* ── Complex test: binary tree with Copy labels, both passes exercised ────────
   LabelTree is recursive → stays Clone-only after the copy pass.
   Labels (bool) are Copy.

   Expected outcomes after both passes:
     Copy pass:
       • LabelTree stays Clone-only (recursive)
       • bool label fields are recognised as Copy after the copy pass

     Borrow pass:
       • tree_any_label:   recursive, returns bool → borrowable
       • tree_all_labels:  recursive, returns bool → borrowable
       • tree_depth:       recursive, returns Nat (constructed, not the param)
                           → borrowable via B-Recursive
       • tree_label_count: recursive, returns Nat → borrowable via B-Recursive
       • tree_mirror:      recursive, constructs a new LabelTree (BNode args
                           are results of recursive calls, not direct param
                           use in return pos) → borrowable via B-Recursive
       • tree_replace_labels: recursive, constructs new tree → borrowable
       • tree_dup:         returns param in both slots → Move → NOT borrowable

   tree_mirror and tree_replace_labels are interesting: they construct and
   return owned LabelTree values, but the original parameter is never directly
   returned.  The recursive calls will use the _borrow variant, so the param
   is only ever borrowed, not moved.                                            *)

datatype label_tree =
    LLeaf bool
  | LNode label_tree label_tree

(* ── Purely observational → borrowable ───────────────────────────────────── *)

fun tree_is_leaf :: "label_tree \<Rightarrow> bool" where
  "tree_is_leaf (LLeaf _) = True"
| "tree_is_leaf (LNode _ _) = False"

fun tree_root_label :: "label_tree \<Rightarrow> bool" where
  "tree_root_label (LLeaf b) = b"
| "tree_root_label (LNode _ _) = False"

(* ── Recursive observation → borrowable via B-Recursive ─────────────────── *)

fun tree_any_label :: "label_tree \<Rightarrow> bool" where
  "tree_any_label (LLeaf b) = b"
| "tree_any_label (LNode l r) = (tree_any_label l \<or> tree_any_label r)"

fun tree_all_labels :: "label_tree \<Rightarrow> bool" where
  "tree_all_labels (LLeaf b) = b"
| "tree_all_labels (LNode l r) = (tree_all_labels l \<and> tree_all_labels r)"

fun tree_depth :: "label_tree \<Rightarrow> nat" where
  "tree_depth (LLeaf _) = 0"
| "tree_depth (LNode l r) = Suc (max (tree_depth l) (tree_depth r))"

fun tree_label_count :: "label_tree \<Rightarrow> nat" where
  "tree_label_count (LLeaf _) = 1"
| "tree_label_count (LNode l r) = tree_label_count l + tree_label_count r"

(* ── Constructing: returns a new tree, never the param itself → borrowable ── *)

fun tree_mirror :: "label_tree \<Rightarrow> label_tree" where
  "tree_mirror (LLeaf b) = LLeaf b"
| "tree_mirror (LNode l r) = LNode (tree_mirror r) (tree_mirror l)"

fun tree_replace_labels :: "label_tree \<Rightarrow> bool \<Rightarrow> label_tree" where
  "tree_replace_labels (LLeaf _) v = LLeaf v"
| "tree_replace_labels (LNode l r) v = LNode (tree_replace_labels l v) (tree_replace_labels r v)"

(* ── Not borrowable: param returned directly → Move demand ─────────────── *)

fun tree_dup :: "label_tree \<Rightarrow> label_tree \<times> label_tree" where
  "tree_dup t = (t, t)"

export_code tree_is_leaf tree_root_label
            tree_any_label tree_all_labels tree_depth tree_label_count
            tree_mirror tree_replace_labels
            tree_dup
  in Rust

end
