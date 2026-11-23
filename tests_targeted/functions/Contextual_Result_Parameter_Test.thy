theory Contextual_Result_Parameter_Test
  imports Applied_Container_Result_Test
begin

text \<open>
  A polymorphic producer has a type parameter without an argument witness, so
  Rust needs explicit generic arguments. Those arguments must retain the
  representation already selected by the enclosing equality dictionary.
  Also cover a witnessed parameter in the same explicit generic argument list:
  its function argument must agree with the type used by the new list result.
\<close>

definition empty_result :: "'a list"
  where "empty_result = []"

definition empty_after :: "bool \<Rightarrow> 'a list"
  where "empty_after b = (if b then [] else [])"

definition paired_result :: "'b \<Rightarrow> 'a list \<times> 'b"
  where "paired_result x = ([], x)"

definition marked_single :: "'a \<Rightarrow> 'a list \<times> 'b option"
  where "marked_single x = ([x], None)"

definition contextual_empty :: bool
  where "contextual_empty =
    equal_values (empty_result :: (bool \<Rightarrow> bool \<Rightarrow> bool) list) []"

definition contextual_after :: "bool \<Rightarrow> bool"
  where "contextual_after b =
    equal_values (empty_after b :: (bool \<Rightarrow> bool \<Rightarrow> bool) list) []"

definition contextual_pair :: "bool \<Rightarrow> bool"
  where "contextual_pair b =
    equal_values (fst (paired_result b) :: (bool \<Rightarrow> bool \<Rightarrow> bool) list) []"

definition contextual_marked :: "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "contextual_marked f =
    equal_values (marked_single f ::
      (bool \<Rightarrow> bool \<Rightarrow> bool) list \<times> bool option)
      ([\<lambda>x y. x \<and> y], None)"

definition ordinary_marker :: "bool \<Rightarrow> bool"
  where "ordinary_marker b =
    (case marked_single b :: bool list \<times> bool option of
      (xs, _) \<Rightarrow> (case xs of [x] \<Rightarrow> x | _ \<Rightarrow> False))"

lemma contextual_result_values:
  "contextual_empty"
  "contextual_after b"
  "contextual_pair b"
  "contextual_marked f = (f = (\<lambda>x y. x \<and> y))"
  "ordinary_marker b = b"
  by (simp_all add: contextual_empty_def contextual_after_def contextual_pair_def
      contextual_marked_def ordinary_marker_def empty_result_def empty_after_def
      paired_result_def marked_single_def equal_values_def)

export_code contextual_empty contextual_after contextual_pair contextual_marked
  ordinary_marker in Rust module_name ContextualResultParameter

end
