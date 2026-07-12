theory paper_example
  imports Main "Rust.Rust_Setup"
begin

datatype ('a, 'b) tree =
    Leaf 'a
  | Branch 'b "('a, 'b) tree" "('a, 'b) tree"

fun duplicate_leaf :: "('a, 'b) tree \<Rightarrow> ('a \<times> 'a) option" where
  "duplicate_leaf (Leaf x) = Some (x, x)"
| "duplicate_leaf (Branch _ _ _) = None"

definition use_duplicate_leaf :: "(bool, nat) tree \<Rightarrow> (bool \<times> bool) option" where
  "use_duplicate_leaf t = duplicate_leaf t"

export_code duplicate_leaf use_duplicate_leaf in Rust

end
