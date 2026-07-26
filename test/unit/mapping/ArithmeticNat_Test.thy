theory ArithmeticNat_Test
  imports Main "Rust.Rust_BigInt_Setup"
begin

(* Rust_BigInt_Setup maps integer, int, and nat uniformly to BigInt. *)

definition nat_zero :: nat where
  "nat_zero = 0"

fun count_down :: "nat \<Rightarrow> nat" where
  "count_down 0 = 0"
| "count_down (Suc n) = Suc (count_down n)"

definition nat_branch :: "nat \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> nat" where
  "nat_branch x y z = (if x < y then x + z else y + z)"

definition nat_delta :: "nat \<Rightarrow> nat \<Rightarrow> nat" where
  "nat_delta x y = (if x < y then y - x else x - y)"

definition nat_eq :: "nat \<Rightarrow> nat \<Rightarrow> bool" where
  "nat_eq x y = (x = y)"

definition nat_le :: "nat \<Rightarrow> nat \<Rightarrow> bool" where
  "nat_le x y = (x \<le> y)"

definition nat_lt :: "nat \<Rightarrow> nat \<Rightarrow> bool" where
  "nat_lt x y = (x < y)"

definition nat_clamp :: "integer \<Rightarrow> nat" where
  "nat_clamp k = nat_of_integer k"

definition nat_to_integer :: "nat \<Rightarrow> integer" where
  "nat_to_integer n = integer_of_nat n"

export_code
  nat_zero count_down nat_branch nat_delta nat_eq nat_le nat_lt
  nat_clamp nat_to_integer
  in Rust

end
