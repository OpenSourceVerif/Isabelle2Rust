theory Rust_Improved_Divmod_Setup
  imports
    Rust_Base_Setup
    "Polynomial_Interpolation.Improved_Code_Equations"
begin

text \<open>
  Optional adapter for AFP's guarded divmod_abs' helper. Import it alongside
  the desired numeric profile and declare Polynomial_Interpolation as a
  session dependency. Ordinary Rust clients need not import AFP.

  The source definition specifies this helper only for nonnegative arguments.
  Its callers in the improved integer and natural division equations establish
  those conditions. Preserve that domain explicitly instead of extending an
  external-language division primitive to unspecified inputs. On the valid
  domain, Code_Numeral.divmod_abs already has the selected profile's existing
  implementation, including a zero divisor returning (0, dividend).

  Code.abort is logically its delayed argument, so the equation below is a
  theorem even outside the specified domain. Executable Rust stops there via
  the existing abort protocol; the self-reference is never evaluated.
\<close>

lemma rust_afp_divmod_abs_code [code]:
  "divmod_abs' x y =
    (if 0 \<le> x \<and> 0 \<le> y then Code_Numeral.divmod_abs x y
     else Code.abort (STR ''divmod_abs requires nonnegative arguments'')
       (\<lambda>_. divmod_abs' x y))"
  by (simp add: Code.abort_def divmod_abs'_def)

end
