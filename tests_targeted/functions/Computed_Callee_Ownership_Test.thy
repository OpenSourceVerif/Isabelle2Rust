theory Computed_Callee_Ownership_Test
  imports Rust_Base_Setup
begin

text \<open>
  A conditional expression can compute the function immediately applied by an
  outer application. Its condition still evaluates ordinary expressions: a
  non-Copy value passed to a trait method or ordinary function must be cloned
  before a branch captures that same value. Printing a callee expression with
  declaration/pattern wrappers used to suppress these clones and cause E0382.
\<close>

definition callee_select :: "'a::equal \<Rightarrow> 'a \<Rightarrow> bool"
  where "callee_select a b = HOL.equal a b"

definition callee_trait_reuse :: "'a::equal \<Rightarrow> 'a \<Rightarrow> 'a \<Rightarrow> bool"
  where "callee_trait_reuse a b c =
    (if HOL.equal a b then (\<lambda>x. HOL.equal x b) else (\<lambda>x. HOL.equal a x)) c"

definition callee_function_reuse :: "'a::equal \<Rightarrow> 'a \<Rightarrow> 'a \<Rightarrow> bool"
  where "callee_function_reuse a b c =
    (if callee_select a b then (\<lambda>x. HOL.equal x b) else (\<lambda>x. HOL.equal a x)) c"

datatype callee_token = Token bool bool

text \<open>
  The concrete wrapper retains the datatype equality instance for runtime
  checks. Both branches are tested with non-Copy tokens; the generic roots also
  reject accidental dependence on Copy for their class-constrained parameters.
\<close>
definition callee_concrete :: "callee_token \<Rightarrow> callee_token \<Rightarrow> callee_token \<Rightarrow> bool"
  where "callee_concrete a b c = (callee_trait_reuse a b c \<and> callee_function_reuse a b c)"

lemma callee_trait_reuse_value: "callee_trait_reuse a b c = (a = c)"
  by (auto simp add: callee_trait_reuse_def equal)
lemma callee_function_reuse_value: "callee_function_reuse a b c = (a = c)"
  by (auto simp add: callee_function_reuse_def callee_select_def equal)

export_code callee_trait_reuse callee_function_reuse callee_concrete
  in Rust module_name ComputedCalleeOwnership

end
