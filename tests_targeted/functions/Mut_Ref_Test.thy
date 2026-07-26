theory Mut_Ref_Test
  imports Main "Rust.Rust_Base_Setup"
begin

datatype nat_list =
    Nil
  | Cons nat nat_list

fun sum_acc :: "nat_list \<Rightarrow> nat \<Rightarrow> nat" where
  "sum_acc Nil acc = acc"
| "sum_acc (Cons x xs) acc = sum_acc xs (acc + x)"

definition sum :: "nat_list \<Rightarrow> nat" where
  "sum xs = sum_acc xs 0"

export_code sum in Rust

end