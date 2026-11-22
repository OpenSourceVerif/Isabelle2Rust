theory ArithmeticSourceBigInt_Test
  imports "Rust.Rust_Source_BigInt_Setup"
begin

definition difference_is :: "'a::{minus,equal} \<Rightarrow> 'a \<Rightarrow> 'a \<Rightarrow> bool" where
  "difference_is x y z = (x - y = z)"

definition mixed_subtraction :: bool where
  "mixed_subtraction = (difference_is (1::nat) 2 0 \<and>
    difference_is (1::int) 2 (-1) \<and> difference_is (1::integer) 2 (-1))"

definition check_conversions :: bool where
  "check_conversions = (let n = (1361129467683753853853498429727072845824 :: nat);
      k = integer_of_nat n
    in nat_of_integer (-k) = 0 \<and> nat_of_integer k = n \<and>
       integer_of_int (int_of_integer (-k)) = -k \<and> gcd (int_of_integer (-7)) 12 = 1)"

code_printing code_module SourceBigInt_Assertions \<rightharpoonup> (Rust) \<open>
#[cfg(test)]
mod tests {
    use crate::ArithmeticSourceBigInt::*;

    #[test]
    fn subtraction_uses_the_source_type() {
        assert!(mixed_subtraction());
    }

    #[test]
    fn large_conversions_and_signed_patterns() {
        assert!(check_conversions());
    }
}
\<close>

export_code mixed_subtraction check_conversions in Rust module_name ArithmeticSourceBigInt

end
