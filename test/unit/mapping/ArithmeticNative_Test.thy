theory ArithmeticNative_Test
  imports Main "Rust.Rust_Hybrid128_Setup"
begin

unbundle bit_operations_syntax

definition int_affine :: "integer \<Rightarrow> integer \<Rightarrow> integer" where
  "int_affine x y = 3 * x - y + 7"

definition int_div_mod :: "integer \<Rightarrow> integer \<Rightarrow> integer \<times> integer" where
  "int_div_mod x y = (x div y, x mod y)"

definition int_bits :: "integer \<Rightarrow> integer \<Rightarrow> nat \<Rightarrow> integer \<times> bool" where
  "int_bits x y n = (take_bit n ((x AND y) OR (x XOR y)), bit x n)"

definition int_large :: integer where
  "int_large = 340282366920938463463374607431768211456"

definition nat_arithmetic :: "nat \<Rightarrow> nat \<Rightarrow> nat \<times> nat \<times> nat" where
  "nat_arithmetic x y = (x + y, x - y, x * y)"

definition nat_div_mod :: "nat \<Rightarrow> nat \<Rightarrow> nat \<times> nat" where
  "nat_div_mod x y = (x div y, x mod y)"

definition nat_bits :: "nat \<Rightarrow> nat \<Rightarrow> nat" where
  "nat_bits x n = flip_bit n (take_bit (n + 1) (push_bit n x))"

definition native_power :: "integer \<Rightarrow> nat \<Rightarrow> integer" where
  "native_power x n = x ^ n"

export_code
  int_affine int_div_mod int_bits int_large nat_arithmetic nat_div_mod nat_bits
  native_power
  in Rust module_name ArithmeticNative_Test file_prefix arithmetic_native_test

end
