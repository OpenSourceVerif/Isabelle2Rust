theory Case_Function_Arity_Test
  imports Rust_Base_Setup
begin

text \<open>
  A case may return a pattern-bound function. Its full result type is recorded
  by the primitive application even though that binder is unavailable in the
  surrounding variable context. Partial applications retain every missing arrow.
\<close>

datatype arity_callback = ArityCallback "bool \<Rightarrow> bool \<Rightarrow> bool"

definition partial_case_callback ::
  "arity_callback \<Rightarrow> bool \<Rightarrow> (bool \<Rightarrow> bool) option"
  where "partial_case_callback box b = Some ((case box of ArityCallback f \<Rightarrow> f) b)"

definition full_case_callback :: "arity_callback \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool"
  where "full_case_callback box a b = (case box of ArityCallback f \<Rightarrow> f) a b"

definition option_case_callback ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool) option \<Rightarrow>
    bool \<Rightarrow> (bool \<Rightarrow> bool) option"
  where "option_case_callback box b =
    Some ((case box of None \<Rightarrow> (\<lambda>a c. a \<and> c) | Some f \<Rightarrow> f) b)"

lemma arity_observations:
  "partial_case_callback (ArityCallback f) b = Some (f b)"
  "full_case_callback (ArityCallback f) a b = f a b"
  "option_case_callback (Some f) b = Some (f b)"
  by (simp_all add: partial_case_callback_def full_case_callback_def option_case_callback_def)

export_code partial_case_callback full_case_callback option_case_callback
  in Rust module_name CaseFunctionArity

end
