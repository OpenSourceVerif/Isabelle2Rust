theory High_Level_Mapping_Peano_Test
  imports Main "Rust.Rust_Base_Setup"
begin

definition nat_branch :: "nat \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> nat" where
  "nat_branch x y z = (if x < y then x + z else y + z)"

definition nat_delta :: "nat \<Rightarrow> nat \<Rightarrow> nat" where
  "nat_delta x y = (if x < y then y - x else x - y)"

definition int_affine :: "int \<Rightarrow> int \<Rightarrow> int" where
  "int_affine x y = 3 * x - y + 7"

definition int_branch :: "int \<Rightarrow> int \<Rightarrow> int" where
  "int_branch x y = (if x < y then y - x else x - y)"

export_code
  nat_branch
  nat_delta
  int_affine
  int_branch
  in Rust

end
