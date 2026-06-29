theory Count_True_Test
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

export_code count in Rust

end
