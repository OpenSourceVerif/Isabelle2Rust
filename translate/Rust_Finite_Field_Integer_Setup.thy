theory Rust_Finite_Field_Integer_Setup
  imports
    Rust_Improved_Divmod_Setup
    "Berlekamp_Zassenhaus.Finite_Field_Record_Based"
begin

text \<open>
  Optional adapter for the integer-backed finite-field implementation.
  Import it alongside the selected numeric profile and declare the
  Berlekamp_Zassenhaus session dependency. The imported divmod adapter supplies
  the nonnegative magnitude helper used by ordinary integer remainder code.

  mod_nonneg_pos is specified only for a nonnegative dividend and a strictly
  positive modulus. Its finite-field callers establish those conditions.
  Preserve that domain and reuse ordinary integer modulo there. Code.abort
  retains the original HOL value via its delayed argument outside the domain,
  while executable Rust reports the unsupported call without evaluating it.
\<close>

lemma rust_afp_mod_nonneg_pos_code [code]:
  "mod_nonneg_pos x y =
    (if 0 \<le> x \<and> 0 < y then x mod y
     else Code.abort (STR ''mod_nonneg_pos requires a nonnegative dividend and positive modulus'')
       (\<lambda>_. mod_nonneg_pos x y))"
  by (simp add: Code.abort_def mod_nonneg_pos_def)

end
