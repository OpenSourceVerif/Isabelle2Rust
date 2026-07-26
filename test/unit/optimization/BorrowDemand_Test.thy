theory BorrowDemand_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Copy-valued fields remain compatible with borrowing a recursive value. *)

datatype ce_tree =
    CELeaf bool
  | CENode ce_tree ce_tree

datatype ce_holder =
  CEHolder bool ce_tree

fun ce_leaf_val :: "ce_tree \<Rightarrow> bool" where
  "ce_leaf_val (CELeaf b) = b"
| "ce_leaf_val (CENode _ _) = False"

fun ce_holder_flag :: "ce_holder \<Rightarrow> bool" where
  "ce_holder_flag (CEHolder b _) = b"

fun ce_leaf_negated :: "ce_tree \<Rightarrow> bool" where
  "ce_leaf_negated (CELeaf b) = (\<not> b)"
| "ce_leaf_negated (CENode _ _) = True"

fun ce_is_single_leaf :: "ce_tree \<Rightarrow> bool" where
  "ce_is_single_leaf (CELeaf _) = True"
| "ce_is_single_leaf (CENode (CELeaf _) (CELeaf _)) = True"
| "ce_is_single_leaf _ = False"

(* Direct returns and constructor arguments create Move demand. *)

datatype move_tree =
    MLeaf bool
  | MNode move_tree move_tree

fun mtree_identity :: "move_tree \<Rightarrow> move_tree" where
  "mtree_identity t = t"

fun mtree_select :: "bool \<Rightarrow> move_tree \<Rightarrow> move_tree \<Rightarrow> move_tree" where
  "mtree_select True l _ = l"
| "mtree_select False _ r = r"

fun mtree_make_node :: "move_tree \<Rightarrow> move_tree \<Rightarrow> move_tree" where
  "mtree_make_node l r = MNode l r"

fun mtree_wrap :: "move_tree \<Rightarrow> move_tree" where
  "mtree_wrap t = MNode (MLeaf True) t"

(* Observational uses provide the positive contrast. *)

fun mtree_is_leaf :: "move_tree \<Rightarrow> bool" where
  "mtree_is_leaf (MLeaf _) = True"
| "mtree_is_leaf (MNode _ _) = False"

fun mtree_leaf_val :: "move_tree \<Rightarrow> bool" where
  "mtree_leaf_val (MLeaf b) = b"
| "mtree_leaf_val (MNode _ _) = False"

export_code
  ce_leaf_val ce_holder_flag ce_leaf_negated ce_is_single_leaf mtree_identity
  mtree_select mtree_make_node mtree_wrap mtree_is_leaf mtree_leaf_val
  in Rust

end
