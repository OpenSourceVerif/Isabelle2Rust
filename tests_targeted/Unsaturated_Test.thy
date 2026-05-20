theory Unsaturated_Test
  imports Main "Rust.Rust_Setup" "Go.Go_Setup"
begin

definition add_n_2 ::  "int \<Rightarrow> (int \<Rightarrow> (int \<Rightarrow> int))" where
  "add_n_2 n \<equiv> (\<lambda>x. (\<lambda>y. x + y + n))"

definition test_add_n_2 :: "int \<Rightarrow> (int \<Rightarrow> int)" where
  "test_add_n_2 x \<equiv> (\<lambda>y. ((add_n_2 1) x) y)"

export_code add_n_2 test_add_n_2 in Rust


definition add_n_3 ::  "int \<Rightarrow> int \<Rightarrow> (int \<Rightarrow> (int \<Rightarrow> int))" where
  "add_n_3 n x = (\<lambda>y. (\<lambda>z.  x + y + z + n))"

definition test_add_n_3 :: "int \<Rightarrow> int \<Rightarrow> (int \<Rightarrow> int)" where
  "test_add_n_3 x = (\<lambda>y. \<lambda>z. ((add_n_3 1 z) x) y)"

export_code add_n_3 test_add_n_3 in Rust

definition add :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "add x y z = x + y + z"

definition test_add :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "test_add n = add n"

export_code test_add in Go
export_code test_add in Rust

end