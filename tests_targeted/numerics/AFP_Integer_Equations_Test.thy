theory AFP_Integer_Equations_Test
  imports Rust_BigInt_Setup Rust_Optimize_Integer_Setup
begin

text \<open>
  Regression for the two AFP integer constants that previously reached Rust
  target projection without code equations. Check the original constants,
  their use inside another definition, negative exponents, and the total
  logarithm on zero and negative inputs. The runtime companion checks broader
  ranges and representation boundaries against independent numeric oracles.
\<close>

definition afp_integer_observations :: "integer \<Rightarrow> integer \<Rightarrow> integer \<times> integer"
  where "afp_integer_observations a n = (power_integer a n, log2_integer a)"

lemma afp_negative_exponent:
  "n \<le> 0 \<Longrightarrow> power_integer a n = 1"
  by (simp add: rust_afp_power_integer_code)

lemma afp_zero_power_zero: "power_integer 0 0 = 1"
  by (simp add: rust_afp_power_integer_code)

lemma afp_log_zero: "log2_integer 0 = 0"
  by (simp add: rust_afp_log2_integer_code)

lemma afp_log_negative: "log2_integer (-8) = 3"
  by (simp add: rust_afp_log2_integer_code compute_bitlen)

export_code power_integer log2_integer afp_integer_observations
  in Rust module_name AFPInteger

end
