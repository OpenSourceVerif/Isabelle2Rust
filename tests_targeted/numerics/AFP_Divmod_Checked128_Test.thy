theory AFP_Divmod_Checked128_Test
  imports Rust_Checked128_Setup Rust_Improved_Divmod_Setup "Polynomial_Interpolation.Divmod_Int"
begin

text \<open>
  AFP's improved quotient/remainder code calls divmod_abs' on nonnegative
  magnitudes, but the helper previously had no Rust code equation. Export the
  guarded helper itself, signed Divmod_Int.divmod_int, and natural divmod.
  The runtime companions cover all signs, both zero arguments, large values,
  and direct out-of-domain calls which must abort rather than invent values.
\<close>

definition afp_guarded_divmod :: "integer \<Rightarrow> integer \<Rightarrow> integer \<times> integer"
  where "afp_guarded_divmod x y = divmod_abs' x y"

definition afp_signed_divmod :: "int \<Rightarrow> int \<Rightarrow> int \<times> int"
  where "afp_signed_divmod x y = Divmod_Int.divmod_int x y"

definition afp_natural_divmod :: "nat \<Rightarrow> nat \<Rightarrow> nat \<times> nat"
  where "afp_natural_divmod x y = Euclidean_Rings.divmod_nat x y"

lemma afp_signed_observation:
  "afp_signed_divmod (-7) 3 = (-3, 2)"
  "afp_signed_divmod 7 (-3) = (-3, -2)"
  "afp_signed_divmod (-7) 0 = (0, -7)"
  by (simp_all add: afp_signed_divmod_def Divmod_Int.divmod_int_def)

lemma afp_guarded_zero:
  "0 \<le> x \<Longrightarrow> afp_guarded_divmod x 0 = (0, x)"
  by (simp add: afp_guarded_divmod_def divmod_abs'_def divmod_abs_def)

export_code afp_guarded_divmod afp_signed_divmod afp_natural_divmod
  in Rust module_name AFPDivmod

end
