theory Rust_Optimize_Integer_Setup
  imports
    Rust_Base_Setup
    "Affine_Arithmetic.Optimize_Integer"
    "HOL-Library.Log_Nat"
begin

text \<open>
  Optional AFP adapter for Optimize_Integer's lifted power and logarithm.
  Import this theory alongside the selected numeric profile, for example
  Rust_BigInt_Setup or Rust_Checked128_Setup. It requires the AFP
  Affine_Arithmetic session; ordinary Rust clients need not import AFP.

  The AFP theory provides SML printings but no computational equations for
  these two constants. Supply proved equations using existing integer
  operations, without introducing target syntax or changing the Rust printer.
  The power equation preserves nat's truncation of negative exponents to zero.
  These ordinary code equations apply to the importing theory context; existing
  native printings for other targets continue to take precedence.
\<close>

context includes integer.lifting begin

text \<open>
  Binary exponentiation uses one recursive result at each halved exponent.
  Multiplying the squared half-result by the original base also avoids squaring
  a large base unnecessarily when the exponent is one.
\<close>

lemma rust_afp_power_half:
  fixes a :: int and n :: nat
  shows "a ^ n = (if n mod 2 = 0 then (a ^ (n div 2)) * (a ^ (n div 2))
    else a * ((a ^ (n div 2)) * (a ^ (n div 2))))"
proof -
  have exponent: "n = n div 2 + n div 2 + n mod 2" by presburger
  have remainder: "n mod 2 = 0 \<or> n mod 2 = 1" by presburger
  have "a ^ n = a ^ (n div 2 + n div 2 + n mod 2)"
    using exponent by simp
  also have "... = (a ^ (n div 2)) * (a ^ (n div 2)) * a ^ (n mod 2)"
    by (simp add: power_add)
  also have "... = (if n mod 2 = 0 then (a ^ (n div 2)) * (a ^ (n div 2))
    else a * ((a ^ (n div 2)) * (a ^ (n div 2))))"
    using remainder by (auto simp: algebra_simps)
  finally show ?thesis .
qed

lemma rust_afp_power_int_binary:
  "power_int a b = (if b \<le> 0 then 1 else
     let half = power_int a (b div 2)
     in if b mod 2 = 0 then half * half else a * (half * half))"
proof (cases "b \<le> 0")
  case True
  then show ?thesis by (simp add: power_int_def)
next
  case False
  have positive: "0 \<le> b" using False by simp
  have mod: "nat b mod 2 = nat (b mod 2)"
    using positive by (simp add: nat_mod_distrib)
  have nonnegative: "0 \<le> b mod 2" by simp
  have mod_zero: "(nat b mod 2 = 0) = (b mod 2 = 0)"
    unfolding mod using nonnegative by auto
  show ?thesis using rust_afp_power_half[of a "nat b"] False
    by (simp add: power_int_def Let_def nat_div_distrib mod_zero)
qed

lemma rust_afp_power_integer_code [code]:
  "power_integer a b = (if b \<le> 0 then 1 else
     let half = power_integer a (b div 2)
     in if b mod 2 = 0 then half * half else a * (half * half))"
  by transfer (rule rust_afp_power_int_binary)

text \<open>
  Isabelle's real logarithm is total: ln 0 = 0 and ln (-x) = ln x.
  Compute the bit length of floor (abs a / 2), which equals this floor-logarithm
  even for zero and unit magnitudes. Dividing before negation avoids forming
  abs MIN in a bounded signed integer profile; every intermediate still fits
  when the input fits. The equations remain theorems over unbounded HOL int.
\<close>

lemma rust_afp_log2_abs: "log2 a = log2 (abs a)"
  by (simp add: log2_def log_def ln_real_def)

lemma rust_afp_log2_bitlen_sub:
  "log2 a = (if a = 0 then 0 else bitlen (abs a) - 1)"
  using rust_afp_log2_abs[of a] by (simp add: log2_def bitlen_alt_def log_def)


lemma rust_afp_log2_bitlen_half: "log2 a = bitlen (abs a div 2)"
  using compute_bitlen[of "abs a"]
  by (cases "a = 0") (auto simp: rust_afp_log2_bitlen_sub)

lemma rust_afp_abs_half:
  fixes a :: int
  shows   "abs a div 2 = (if a < 0 then -(a div 2) - a mod 2 else a div 2)"
  by (auto simp: abs_if; presburger)

lemma rust_afp_log2_integer_code [code]:
  "log2_integer a = integer_of_int (bitlen
    (let k = int_of_integer a in
     if k < 0 then -(k div 2) - k mod 2 else k div 2))"
  by transfer (simp add: rust_afp_log2_bitlen_half rust_afp_abs_half Let_def)


end

end
