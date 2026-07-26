theory Recursive_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Recursive constructor fields exercise Box unwrapping in function arms. *)

datatype 'a rlist =
    RNil
  | RCons 'a "'a rlist"

fun rlength :: "'a rlist \<Rightarrow> nat" where
  "rlength RNil = 0"
| "rlength (RCons _ xs) = Suc (rlength xs)"

fun rmap :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a rlist \<Rightarrow> 'b rlist" where
  "rmap _ RNil = RNil"
| "rmap f (RCons x xs) = RCons (f x) (rmap f xs)"

fun sum_acc :: "nat rlist \<Rightarrow> nat \<Rightarrow> nat" where
  "sum_acc RNil acc = acc"
| "sum_acc (RCons x xs) acc = sum_acc xs (acc + x)"

definition list_sum :: "nat rlist \<Rightarrow> nat" where
  "list_sum xs = sum_acc xs 0"

fun map_add :: "nat \<Rightarrow> nat rlist \<Rightarrow> nat rlist" where
  "map_add _ RNil = RNil"
| "map_add n (RCons x xs) = RCons (x + n) (map_add n xs)"

export_code
  rlength rmap list_sum map_add
  in Rust

end
