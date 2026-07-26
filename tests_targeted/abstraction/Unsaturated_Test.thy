theory Unsaturated_Test
  imports Main "Rust.Rust_Base_Setup"
begin

definition offset_sum ::  "int \<Rightarrow> (int \<Rightarrow> (int \<Rightarrow> int))" where
  "offset_sum c \<equiv> (\<lambda>x. (\<lambda>y. x + y + c))"

definition test_offset_sum :: "int \<Rightarrow> (int \<Rightarrow> int)" where
  "test_offset_sum x \<equiv> (\<lambda>y. ((offset_sum 1) x) y)"

export_code offset_sum test_offset_sum in Rust


definition add_n_3 ::  "int \<Rightarrow> int \<Rightarrow> (int \<Rightarrow> (int \<Rightarrow> int))" where
  "add_n_3 n x = (\<lambda>y. (\<lambda>z.  x + y + z + n))"

definition test_add_n_3 :: "int \<Rightarrow> int \<Rightarrow> (int \<Rightarrow> int)" where
  "test_add_n_3 x = (\<lambda>y. \<lambda>z. ((add_n_3 1 z) x) y)"

export_code add_n_3 test_add_n_3 in Rust

definition add :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "add x y z = x + y + z"

definition test_add :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int" where
  "test_add n = add n"

export_code test_add in Rust

end
