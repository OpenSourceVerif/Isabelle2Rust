theory Codatatype_Shape_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Finite use of a codatatype constructor shape. This test intentionally avoids
   corecursive values such as infinite streams, which require a lazy encoding. *)
codatatype cotree = CoLeaf | CoNode cotree cotree

definition finite_tree :: cotree where
  "finite_tree = CoNode CoLeaf (CoNode CoLeaf CoLeaf)"

fun is_leaf :: "cotree \<Rightarrow> bool" where
  "is_leaf CoLeaf = True"
| "is_leaf (CoNode _ _) = False"

definition finite_tree_is_leaf :: bool where
  "finite_tree_is_leaf = is_leaf finite_tree"

export_code finite_tree is_leaf finite_tree_is_leaf in Rust

end
