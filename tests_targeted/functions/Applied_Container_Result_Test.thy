theory Applied_Container_Result_Test
  imports Rust_Base_Setup
begin

text \<open>
  A polymorphic apply wrapper returns another function whose result contains
  callbacks. Equality on the callback list selects nested unary functions.
  The expected list representation must survive both applications of the
  wrapper without flattening the callbacks in an intermediate closure.
\<close>

definition wrapped_apply :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a \<Rightarrow> 'b"
  where "wrapped_apply f x = f x"

definition callback_list :: "'a \<Rightarrow> 'b \<Rightarrow> ('a \<Rightarrow> 'b) list"
  where "callback_list a b = [\<lambda>_. b]"

definition equal_values :: "'a::equal \<Rightarrow> 'a \<Rightarrow> bool"
  where "equal_values x y = (x = y)"

definition callback_matches :: "bool \<Rightarrow> bool"
  where "callback_matches b =
    equal_values (wrapped_apply (wrapped_apply callback_list False) (\<lambda>x::bool. x \<and> b)) [\<lambda>_ _. False]"

definition callback_direct_matches :: "bool \<Rightarrow> bool"
  where "callback_direct_matches b =
    equal_values (callback_list False (\<lambda>x::bool. x \<and> b)) [\<lambda>_ _. False]"

lemma callback_matches_value: "callback_matches b = (\<not>b)"
  by (cases b; auto simp: callback_matches_def wrapped_apply_def callback_list_def equal_values_def fun_eq_iff)

lemma callback_direct_matches_value: "callback_direct_matches b = (\<not>b)"
  by (cases b; auto simp: callback_direct_matches_def callback_list_def equal_values_def fun_eq_iff)

export_code equal_values callback_matches callback_direct_matches in Rust module_name AppliedContainerResult

end
