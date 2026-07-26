theory BorrowGlobal_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Package summaries must distinguish same-named functions across modules. *)

datatype borrow_tree =
    BLeaf bool
  | BNode borrow_tree borrow_tree

fun global_borrow_left :: "borrow_tree \<Rightarrow> bool" where
  "global_borrow_left (BLeaf b) = b"
| "global_borrow_left (BNode _ _) = False"

fun global_borrow_right :: "borrow_tree \<Rightarrow> bool" where
  "global_borrow_right (BLeaf _) = True"
| "global_borrow_right (BNode _ _) = False"

definition use_global_borrows :: "borrow_tree \<Rightarrow> bool \<times> bool" where
  "use_global_borrows t = (global_borrow_left t, global_borrow_right t)"

code_identifier
  constant global_borrow_left  \<rightharpoonup> (Rust) "BorrowGlobalLeft.inspect"
| constant global_borrow_right \<rightharpoonup> (Rust) "BorrowGlobalRight.inspect"

export_code
  use_global_borrows
  in Rust

end
