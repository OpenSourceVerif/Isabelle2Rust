theory Borrow_Paper_Example_Test
  imports Main "Rust.Rust_Setup"
begin

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

export_code any_label any_label_twice rebuild in Rust

end
