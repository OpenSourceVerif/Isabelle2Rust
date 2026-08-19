theory Code_Adaption_BigInt_Test
  imports Main "Rust.Rust_BigInt_Setup"
begin

definition nat_branch :: "nat \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> nat" where
  "nat_branch x y z = (if x < y then x + z else y + z)"

export_code nat_branch in Rust

end
