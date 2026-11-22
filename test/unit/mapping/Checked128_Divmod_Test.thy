theory Checked128_Divmod_Test
  imports "Rust.Rust_Checked128_Setup"
begin

definition signed_pair :: "integer \<Rightarrow> integer \<Rightarrow> integer \<times> integer" where
  "signed_pair a b = Code_Numeral.divmod_integer a b"

definition natural_pair :: "nat \<Rightarrow> nat \<Rightarrow> nat \<times> nat" where
  "natural_pair a b = Euclidean_Rings.divmod_nat a b"

code_printing code_module Checked128_Divmod_Assertions \<rightharpoonup> (Rust) \<open>
#[cfg(test)]
mod tests {
    use crate::Checked128Divmod::{natural_pair, signed_pair};

    #[test]
    fn signed_boundaries() {
        assert_eq!(signed_pair(i128::MIN, 2), (i128::MIN / 2, 0));
        assert_eq!(signed_pair(1, i128::MIN), (-1, i128::MIN + 1));
        assert_eq!(signed_pair(-7, 3), (-3, 2));
        assert_eq!(signed_pair(7, -3), (-3, -2));
        assert_eq!(signed_pair(i128::MIN, 0), (0, i128::MIN));
        assert!(std::panic::catch_unwind(|| signed_pair(i128::MIN, -1)).is_err());
    }

    #[test]
    fn unsigned_boundaries() {
        assert_eq!(natural_pair(u128::MAX, 2), (u128::MAX / 2, 1));
        assert_eq!(natural_pair(u128::MAX, 1 << 127), (1, (1 << 127) - 1));
        assert_eq!(natural_pair(u128::MAX, 0), (0, u128::MAX));
    }
}
\<close>

export_code signed_pair natural_pair in Rust module_name Checked128Divmod

end
