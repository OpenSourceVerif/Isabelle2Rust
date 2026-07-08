theory BasicDefinitions_Test
  imports Main "Rust.Rust_Setup"
begin

(* Direct single-equation bodies should be printed without a dispatch match. *)

definition zero_nat :: nat where
  "zero_nat = 0"

definition add3 :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "add3 x y z = x + y + z"

fun add_int :: "int \<Rightarrow> int \<Rightarrow> int" where
  "add_int x y = x + y"

fun add_nat :: "nat \<Rightarrow> nat \<Rightarrow> nat" where
  "add_nat x y = x + y"

definition rust_keyword_arg :: "int \<Rightarrow> int" where
  "rust_keyword_arg loop = loop + 1"

fun max_case :: "int \<Rightarrow> int \<Rightarrow> int" where
  "max_case a b =
    (case a > b of
       True \<Rightarrow> a
     | False \<Rightarrow> b)"

fun max_if :: "int \<Rightarrow> int \<Rightarrow> int" where
  "max_if a b = (if a > b then a else b)"

export_code
  zero_nat add3 add_int add_nat rust_keyword_arg max_case max_if
  in Rust

end
