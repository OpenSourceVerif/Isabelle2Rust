theory Abort_Native_Operand_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  A saturated Code.abort has a known HOL result type even though its Rust body
  diverges. Native integer operators need that type on each operand: a bare
  panic block must not make rustc seek Add, Neg or PartialOrd implementations
  for the never type. The roots cover both binary operand positions, unary
  negation, comparison, a safe branch, a stored callback and a partially applied
  abort. Applying a function-valued abort also consumes a result arrow without
  evaluating its delayed fallback or the later argument expression.
\<close>

definition abort_integer_left :: "String.literal \<Rightarrow> integer \<Rightarrow> integer" where
  "abort_integer_left msg x = Code.abort msg (\<lambda>_. 0) + x"

definition abort_integer_right :: "String.literal \<Rightarrow> integer \<Rightarrow> integer" where
  "abort_integer_right msg x = x + Code.abort msg (\<lambda>_. 0)"

definition abort_integer_negate :: "String.literal \<Rightarrow> integer" where
  "abort_integer_negate msg = - Code.abort msg (\<lambda>_. 0)"

definition abort_integer_compare :: "String.literal \<Rightarrow> integer \<Rightarrow> bool" where
  "abort_integer_compare msg x = (Code.abort msg (\<lambda>_. 0) < x)"

definition abort_integer_safe ::
  "bool \<Rightarrow> String.literal \<Rightarrow> integer \<Rightarrow> integer" where
  "abort_integer_safe enabled msg x =
    (if enabled then Code.abort msg (\<lambda>_. 0) + x else x)"

definition abort_integer_delayed ::
  "String.literal \<Rightarrow> (integer \<Rightarrow> integer) option" where
  "abort_integer_delayed msg = Some (\<lambda>x. Code.abort msg (\<lambda>_. 0) + x)"

definition abort_apply_integer :: "String.literal \<Rightarrow> integer \<Rightarrow> integer" where
  "abort_apply_integer msg x =
    Code.abort msg (\<lambda>_. id)
      (Code.abort (STR ''argument evaluated'') (\<lambda>_. x)) + 1"

definition abort_partial_integer ::
  "String.literal \<Rightarrow> ((unit \<Rightarrow> integer) \<Rightarrow> integer) option" where
  "abort_partial_integer msg = Some (Code.abort msg)"

lemma abort_integer_safe_disabled: "abort_integer_safe False msg x = x"
  by (simp add: abort_integer_safe_def)

export_code abort_integer_left abort_integer_right abort_integer_negate
  abort_integer_compare abort_integer_safe abort_integer_delayed
  abort_apply_integer abort_partial_integer in Rust module_name AbortNativeOperand

end
