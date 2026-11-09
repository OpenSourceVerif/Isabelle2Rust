theory AFP_Field_Modulus_Test
  imports Rust_BigInt_Setup Rust_Finite_Field_Integer_Setup
begin

text \<open>
  The AFP finite-field integer helper previously had neither a Rust printing
  nor an executable equation. Exercise the helper and its actual callers:
  integer-backed field multiplication and binary modular exponentiation.
  Valid inputs must preserve exact modulo results; negative dividends and
  nonpositive moduli must take the existing abort protocol, not receive an
  arbitrary extension of the guarded source definition.
\<close>

definition afp_modulus :: "integer \<Rightarrow> integer \<Rightarrow> integer"
  where "afp_modulus x p = mod_nonneg_pos x p"

definition afp_field_product :: "int \<Rightarrow> int \<Rightarrow> int \<Rightarrow> int"
  where "afp_field_product p x y = mult_p p x y"

definition afp_field_power :: "int \<Rightarrow> int \<Rightarrow> nat \<Rightarrow> int"
  where "afp_field_power p x n = power_p p x n"

lemma afp_modulus_observation:
  "afp_modulus 30 7 = 2"
  by (simp add: afp_modulus_def mod_nonneg_pos_def)

lemma afp_product_observation:
  "afp_field_product 7 5 6 = 2"
  by (simp add: afp_field_product_def mult_p_def)

lemma afp_power_zero:
  "afp_field_power p x 0 = 1"
  by (simp add: afp_field_power_def power_p.simps)

export_code afp_modulus afp_field_product afp_field_power
  in Rust module_name AFPField

end
