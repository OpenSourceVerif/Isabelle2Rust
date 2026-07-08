theory ArithmeticPeano_Test
  imports Main "Rust.Rust_Setup"
begin

(* Without BigInt setup, nat remains the generated Peano datatype. *)

fun peano_count :: "nat \<Rightarrow> nat" where
  "peano_count 0 = 0"
| "peano_count (Suc n) = Suc (peano_count n)"

definition peano_branch :: "nat \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> nat" where
  "peano_branch x y z = (if x < y then x + z else y + z)"

definition peano_delta :: "nat \<Rightarrow> nat \<Rightarrow> nat" where
  "peano_delta x y = (if x < y then y - x else x - y)"

definition peano_compare :: "nat \<Rightarrow> nat \<Rightarrow> bool" where
  "peano_compare x y = (x \<le> y \<and> x \<noteq> y)"

export_code
  peano_count peano_branch peano_delta peano_compare
  in Rust

end
