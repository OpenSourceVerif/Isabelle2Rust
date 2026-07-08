theory CopyBorrow_Test
  imports Main "Rust.Rust_Setup"
begin

(* Overview running example: bool-labelled binary tree, count the true leaves.
   Exercises copy (bool leaf) + borrow (subtrees); stage-2 should be clone-free. *)

datatype tree =
    Leaf bool
  | Branch tree tree

fun count :: "tree \<Rightarrow> nat" where
  "count (Leaf b) = of_bool b"
| "count (Branch l r) = count l + count r"

(* ── Complex test: custom list type exercising both copy and borrow passes ────
   MyList is a recursive type → stays non-Copy after the copy pass.
   bool elements are Copy, so Copy-field uses in functions are Own(CopyUse).

   Expected outcomes after both passes:
     Copy pass:
       • MyList stays Clone-only (recursive with Box)
       • bool stays Copy (primitive)
       • Standalone bool functions get no _copy specialisation (already concrete)

     Borrow pass:
       • list_is_empty:  observational only → borrowable
       • list_head:      returns Copy bool  → Own(CopyUse), borrowable
       • list_length:    recursive, returns Nat (non-Copy constructed value, not
                         the param itself) → fixed-point analysis makes it
                         borrowable via B-Recursive
       • list_any_true:  recursive observation, returns bool → borrowable
       • list_append:    first param is recursively traversed (borrowable);
                         second param is returned directly in the base case
                         (Move demand) → second param NOT borrowable
       • list_dup:       param returned in both slots of the pair → Move → NOT
                         borrowable                                             *)

datatype 'a my_list =
    MyNil
  | MyCons 'a "'a my_list"

(* ── Observational (always borrowable) ──────────────────────────────────────*)

fun list_is_empty :: "'a my_list \<Rightarrow> bool" where
  "list_is_empty MyNil = True"
| "list_is_empty (MyCons _ _) = False"

(* returns a Copy bool from the head → Own(CopyUse) demand → borrowable *)
fun list_head :: "bool my_list \<Rightarrow> bool" where
  "list_head MyNil = False"
| "list_head (MyCons x _) = x"

(* ── Recursive observation (borrowable via B-Recursive fixed-point) ──────── *)

fun list_length :: "'a my_list \<Rightarrow> nat" where
  "list_length MyNil = 0"
| "list_length (MyCons _ xs) = Suc (list_length xs)"

fun list_any_true :: "bool my_list \<Rightarrow> bool" where
  "list_any_true MyNil = False"
| "list_any_true (MyCons x xs) = (x \<or> list_any_true xs)"

fun list_all_true :: "bool my_list \<Rightarrow> bool" where
  "list_all_true MyNil = True"
| "list_all_true (MyCons x xs) = (x \<and> list_all_true xs)"

(* ── Mixed borrowability: first param borrowable, second NOT ─────────────── *)

(* first param is recursively traversed; second param is returned directly in
   the base case → second param has Move demand                               *)
fun list_append :: "'a my_list \<Rightarrow> 'a my_list \<Rightarrow> 'a my_list" where
  "list_append MyNil ys = ys"
| "list_append (MyCons x xs) ys = MyCons x (list_append xs ys)"

(* ── Not borrowable: direct return of parameter ─────────────────────────────*)

fun list_dup :: "'a my_list \<Rightarrow> 'a my_list \<times> 'a my_list" where
  "list_dup xs = (xs, xs)"

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

export_code
  count list_is_empty list_head list_length list_any_true list_all_true list_append
  list_dup tree_is_leaf tree_root_label tree_any_label tree_all_labels tree_depth
  tree_label_count tree_mirror tree_replace_labels tree_dup
  in Rust

end
