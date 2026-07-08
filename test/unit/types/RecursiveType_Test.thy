theory RecursiveType_Test
  imports Main "Rust.Rust_Setup"
begin

(* Direct recursive datatype. *)
datatype 'a rlist = RNil | RCons 'a "'a rlist"

fun singleton :: "'a \<Rightarrow> 'a rlist" where
  "singleton x = RCons x RNil"

fun is_empty :: "'a rlist \<Rightarrow> bool" where
  "is_empty RNil = True"
| "is_empty (RCons _ _) = False"

fun head_or :: "'a \<Rightarrow> 'a rlist \<Rightarrow> 'a" where
  "head_or d RNil = d"
| "head_or _ (RCons x _) = x"

(* Recursion through a type argument. *)
datatype tree = Leaf | Tree "tree list"

fun wrap_tree :: "tree \<Rightarrow> tree" where
  "wrap_tree t = Tree [t]"

fun tree_is_leaf :: "tree \<Rightarrow> bool" where
  "tree_is_leaf Leaf = True"
| "tree_is_leaf (Tree _) = False"

export_code
  singleton is_empty head_or wrap_tree tree_is_leaf
  in Rust

end
