theory IntegratedTree_Test
  imports Main "Rust.Rust_Base_Setup"
begin

datatype flag_pair =
  Flags bool bool

datatype flag_tree =
    FTLeaf flag_pair
  | FTNode flag_tree flag_pair flag_tree

(* Copy fields inside a recursive, non-Copy tree. *)

fun flags_any :: "flag_pair \<Rightarrow> bool" where
  "flags_any (Flags x y) = (x \<or> y)"

fun flags_all :: "flag_pair \<Rightarrow> bool" where
  "flags_all (Flags x y) = (x \<and> y)"

fun flags_swap :: "flag_pair \<Rightarrow> flag_pair" where
  "flags_swap (Flags x y) = Flags y x"

fun ftree_is_leaf :: "flag_tree \<Rightarrow> bool" where
  "ftree_is_leaf (FTLeaf _) = True"
| "ftree_is_leaf (FTNode _ _ _) = False"

fun ftree_root_any :: "flag_tree \<Rightarrow> bool" where
  "ftree_root_any (FTLeaf p) = flags_any p"
| "ftree_root_any (FTNode _ p _) = flags_any p"

(* Recursive observations exercise shared borrowing across both branches. *)

fun ftree_size :: "flag_tree \<Rightarrow> nat" where
  "ftree_size (FTLeaf _) = 1"
| "ftree_size (FTNode l _ r) = Suc (ftree_size l + ftree_size r)"

fun ftree_height :: "flag_tree \<Rightarrow> nat" where
  "ftree_height (FTLeaf _) = 1"
| "ftree_height (FTNode l _ r) = Suc (max (ftree_height l) (ftree_height r))"

fun ftree_any :: "flag_tree \<Rightarrow> bool" where
  "ftree_any (FTLeaf p) = flags_any p"
| "ftree_any (FTNode l p r) =
     (ftree_any l \<or> flags_any p \<or> ftree_any r)"

fun ftree_all :: "flag_tree \<Rightarrow> bool" where
  "ftree_all (FTLeaf p) = flags_all p"
| "ftree_all (FTNode l p r) =
     (ftree_all l \<and> flags_all p \<and> ftree_all r)"

fun ftree_true_pairs :: "flag_tree \<Rightarrow> nat" where
  "ftree_true_pairs (FTLeaf p) = (if flags_all p then 1 else 0)"
| "ftree_true_pairs (FTNode l p r) =
     ftree_true_pairs l + (if flags_all p then 1 else 0) + ftree_true_pairs r"

fun ftree_same_shape :: "flag_tree \<Rightarrow> flag_tree \<Rightarrow> bool" where
  "ftree_same_shape (FTLeaf _) (FTLeaf _) = True"
| "ftree_same_shape (FTLeaf _) (FTNode _ _ _) = False"
| "ftree_same_shape (FTNode _ _ _) (FTLeaf _) = False"
| "ftree_same_shape (FTNode l _ r) (FTNode l' _ r') =
     (ftree_same_shape l l' \<and> ftree_same_shape r r')"

(* Rebuilds test recursive calls that construct fresh owned results. *)

fun ftree_mirror :: "flag_tree \<Rightarrow> flag_tree" where
  "ftree_mirror (FTLeaf p) = FTLeaf p"
| "ftree_mirror (FTNode l p r) =
     FTNode (ftree_mirror r) p (ftree_mirror l)"

fun ftree_flip :: "flag_tree \<Rightarrow> flag_tree" where
  "ftree_flip (FTLeaf p) = FTLeaf (flags_swap p)"
| "ftree_flip (FTNode l p r) =
     FTNode (ftree_flip l) (flags_swap p) (ftree_flip r)"

fun ftree_leftmost :: "flag_tree \<Rightarrow> flag_pair" where
  "ftree_leftmost (FTLeaf p) = p"
| "ftree_leftmost (FTNode l _ _) = ftree_leftmost l"

fun ftree_replace_leftmost :: "flag_pair \<Rightarrow> flag_tree \<Rightarrow> flag_tree" where
  "ftree_replace_leftmost p (FTLeaf _) = FTLeaf p"
| "ftree_replace_leftmost p (FTNode l q r) =
     FTNode (ftree_replace_leftmost p l) q r"

(* Traversals combine recursive tree results with recursive lists. *)

fun ftree_preorder :: "flag_tree \<Rightarrow> flag_pair list" where
  "ftree_preorder (FTLeaf p) = [p]"
| "ftree_preorder (FTNode l p r) = p # (ftree_preorder l @ ftree_preorder r)"

fun ftree_inorder :: "flag_tree \<Rightarrow> flag_pair list" where
  "ftree_inorder (FTLeaf p) = [p]"
| "ftree_inorder (FTNode l p r) = ftree_inorder l @ p # ftree_inorder r"

fun ftree_postorder :: "flag_tree \<Rightarrow> flag_pair list" where
  "ftree_postorder (FTLeaf p) = [p]"
| "ftree_postorder (FTNode l p r) = ftree_postorder l @ ftree_postorder r @ [p]"

(* Mixed calls distinguish observed parameters from returned parameters. *)

definition ftree_select :: "bool \<Rightarrow> flag_tree \<Rightarrow> flag_tree \<Rightarrow> flag_tree" where
  "ftree_select b l r = (if b then l else r)"

definition ftree_observe_then_select ::
  "flag_tree \<Rightarrow> flag_tree \<Rightarrow> flag_tree" where
  "ftree_observe_then_select observed result =
    (if ftree_any observed then result else ftree_mirror result)"

definition ftree_query_pair :: "flag_tree \<Rightarrow> bool \<times> nat" where
  "ftree_query_pair t = (ftree_any t, ftree_height t)"

definition ftree_transform_chain :: "flag_tree \<Rightarrow> flag_tree" where
  "ftree_transform_chain t =
    (let x = t;
         x = ftree_flip x;
         x = ftree_mirror x
     in x)"

export_code
  flags_any flags_all flags_swap ftree_is_leaf ftree_root_any ftree_size
  ftree_height ftree_any ftree_all ftree_true_pairs ftree_same_shape
  ftree_mirror ftree_flip ftree_leftmost ftree_replace_leftmost ftree_preorder
  ftree_inorder ftree_postorder ftree_select ftree_observe_then_select
  ftree_query_pair ftree_transform_chain
  in Rust

end
