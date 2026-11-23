theory Function_Value_Container_Result_Test
  imports Applied_Container_Result_Test
begin

text \<open>
  An ordinary function value has the same container result representation as
  its Rust function item. Passing that value through a polymorphic apply must
  preserve both declared function-result boundaries and dictionary-selected
  container fields, without converting a materialized container.
\<close>

definition inspect_callbacks :: "bool \<Rightarrow> bool list"
  where "inspect_callbacks b =
    map (\<lambda>f. f False True)
      (wrapped_apply (wrapped_apply callback_list False) (\<lambda>x. x \<and> b))"

definition inspect_callbacks_direct :: "bool \<Rightarrow> bool list"
  where "inspect_callbacks_direct b =
    map (\<lambda>f. f False True) (callback_list False (\<lambda>x. x \<and> b))"

definition selected_producer :: "bool \<Rightarrow> (bool \<Rightarrow> bool \<Rightarrow> bool) set"
  where "selected_producer b = {f. f False False = b}"

definition inspect_named :: "bool \<Rightarrow> bool set"
  where "inspect_named b =
    image (\<lambda>f. f True False) (wrapped_apply selected_producer b)"

definition inspect_named_direct :: "bool \<Rightarrow> bool set"
  where "inspect_named_direct b = image (\<lambda>f. f True False) (selected_producer b)"

definition forwarded_selected :: "bool \<Rightarrow> (bool \<Rightarrow> bool \<Rightarrow> bool) set"
  where "forwarded_selected b = wrapped_apply selected_producer b"

definition delayed_selected ::
  "bool \<Rightarrow> unit \<Rightarrow> (bool \<Rightarrow> bool \<Rightarrow> bool) set"
  where "delayed_selected b = (\<lambda>_. selected_producer b)"

definition inspect_delayed :: "bool \<Rightarrow> bool set"
  where "inspect_delayed b =
    image (\<lambda>f. f True False) (wrapped_apply (delayed_selected b) ())"

lemma callback_observations:
  "inspect_callbacks b = [b]"
  "inspect_callbacks_direct b = [b]"
  by (simp_all add: inspect_callbacks_def inspect_callbacks_direct_def
      wrapped_apply_def callback_list_def)

lemma named_observations:
  "inspect_named False = {False, True}"
  "inspect_named True = {False, True}"
  "inspect_named_direct False = {False, True}"
  "inspect_named_direct True = {False, True}"
  "inspect_delayed False = {False, True}"
  "inspect_delayed True = {False, True}"
  by (eval)+

export_code inspect_callbacks inspect_callbacks_direct inspect_named inspect_named_direct
  forwarded_selected delayed_selected inspect_delayed
  in Rust module_name FunctionValueContainerResult

end
