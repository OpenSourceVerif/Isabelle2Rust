theory ArithmeticDashu_Test
  imports "Rust.Rust_Dashu_Setup"
begin

definition generic_sub :: "'a::minus \<Rightarrow> 'a \<Rightarrow> 'a" where
  "generic_sub x y = x - y"

definition check_sub :: bool where
  "check_sub = (generic_sub (1 :: nat) 2 = 0 \<and> generic_sub (1 :: int) 2 = -1)"

definition check_div_mod :: bool where
  "check_div_mod = (let x = (-17 :: int) in
    x div 5 = -4 \<and> x mod 5 = 3 \<and> 17 div (-5 :: int) = -4 \<and>
    17 mod (-5 :: int) = -3 \<and> x div 0 = 0 \<and> x mod 0 = x)"

definition check_large :: bool where
  "check_large = (let n = (2^160 :: nat) in
    integer_of_nat n = 1461501637330902918203684832716283019655932542976 \<and>
    nat_of_integer (integer_of_nat n + 1) = n + 1)"

code_printing code_module Dashu_Assertions \<rightharpoonup> (Rust) \<open>
#[cfg(test)]
mod tests {
    use crate::ArithmeticDashu::*;
    #[test]
    fn subtraction() { assert!(check_sub()); }
    #[test]
    fn division_and_remainder() { assert!(check_div_mod()); }
    #[test]
    fn large_conversion() { assert!(check_large()); }
}
\<close>

export_code check_sub check_div_mod check_large in Rust module_name ArithmeticDashu

end
