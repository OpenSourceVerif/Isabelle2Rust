theory Lists_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* List syntax, literals, and simple user datatypes should coexist. *)

definition literal_length :: nat where
  "literal_length \<equiv> length [1::nat, 2, 3]"

datatype 'a simple_list =
    SNil
  | SCons 'a "'a simple_list"

fun simple_length :: "'a simple_list \<Rightarrow> nat" where
  "simple_length SNil = 0"
| "simple_length (SCons _ xs) = Suc (simple_length xs)"

fun simple_cons_twice :: "'a \<Rightarrow> 'a simple_list \<Rightarrow> 'a simple_list" where
  "simple_cons_twice x xs = SCons x (SCons x xs)"

export_code
  literal_length simple_length simple_cons_twice
  in Rust

end
