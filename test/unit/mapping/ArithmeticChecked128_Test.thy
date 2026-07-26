theory ArithmeticChecked128_Test
  imports Main "Rust.Rust_Checked128_Setup"
begin

unbundle bit_operations_syntax

definition checked_int_arithmetic ::
    "integer \<Rightarrow> integer \<Rightarrow> integer \<times> integer \<times> integer" where
  "checked_int_arithmetic x y = (x + y, x - y, x * y)"

definition checked_int_div_mod :: "integer \<Rightarrow> integer \<Rightarrow> integer \<times> integer" where
  "checked_int_div_mod x y = (x div y, x mod y)"

definition checked_nat_arithmetic :: "nat \<Rightarrow> nat \<Rightarrow> nat \<times> nat \<times> nat" where
  "checked_nat_arithmetic x y = (x + y, x - y, x * y)"

definition checked_conversions :: "integer \<Rightarrow> nat \<Rightarrow> nat \<times> integer" where
  "checked_conversions x n = (nat_of_integer x, integer_of_nat n)"

definition checked_bits :: "integer \<Rightarrow> nat \<Rightarrow> integer \<times> bool" where
  "checked_bits x n = (take_bit n (push_bit n x), bit x n)"

definition checked_power :: "integer \<Rightarrow> nat \<Rightarrow> integer" where
  "checked_power x n = x ^ n"

export_code
  checked_int_arithmetic checked_int_div_mod checked_nat_arithmetic
  checked_conversions checked_bits checked_power
  in Rust module_name ArithmeticChecked128_Test file_prefix arithmetic_checked128_test

end
