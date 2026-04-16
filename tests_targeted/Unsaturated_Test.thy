theory Unsaturated_Test
  imports Main "Rust.Rust_Setup"
begin

definition add_n_2 ::  "int \<Rightarrow> (int \<Rightarrow> (int \<Rightarrow> int))" where
  "add_n_2 n \<equiv> (\<lambda>x. (\<lambda>y. x + y + n))"

definition test_add_n_2 :: "int \<Rightarrow> (int \<Rightarrow> int)" where
  "test_add_n_2 x \<equiv> (\<lambda>y. ((add_n_2 1) x) y)"

export_code add_n_2 test_add_n_2 in Rust

end