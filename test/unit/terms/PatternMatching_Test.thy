theory PatternMatching_Test
  imports Main "Rust.Rust_Base_Setup"
begin

fun neg :: "bool \<Rightarrow> bool" where
  "neg b = (case b of True \<Rightarrow> False | False \<Rightarrow> True)"

datatype color = Red | Green | Blue | Other nat

fun is_primary :: "color \<Rightarrow> bool" where
  "is_primary Red = True"
| "is_primary Green = True"
| "is_primary Blue = True"
| "is_primary _ = False"

fun case_list1 :: "'a list \<Rightarrow> bool" where
  "case_list1 xs = (case xs of [] \<Rightarrow> False | [x] \<Rightarrow> True | _ \<Rightarrow> False)"

fun case_list2 :: "int list \<Rightarrow> int" where
  "case_list2 xs = (case xs of [] \<Rightarrow> 0 | [x] \<Rightarrow> x * 3 | _ \<Rightarrow> 0)"

fun get_or_zero :: "int option \<Rightarrow> int" where
  "get_or_zero x = (case x of None \<Rightarrow> 0 | Some n \<Rightarrow> n)"

fun head_nat :: "nat list \<Rightarrow> nat" where
  "head_nat (x # xs) = x"

definition first_or_chain :: "nat list \<Rightarrow> nat list \<Rightarrow> nat" where
  "first_or_chain xs ys = head_nat (xs @ ys)"

datatype ilist = INil | ICons int ilist

fun second_or_zero :: "ilist \<Rightarrow> int" where
  "second_or_zero (ICons _ (ICons y _)) = y"
| "second_or_zero _ = 0"

fun first_and_tail :: "'a list \<Rightarrow> ('a \<times> 'a list) option" where
  "first_and_tail [] = None"
| "first_and_tail (x # xs) = Some (x, xs)"

export_code
  neg is_primary case_list1 case_list2 get_or_zero head_nat first_or_chain
  second_or_zero first_and_tail
  in Rust

end
