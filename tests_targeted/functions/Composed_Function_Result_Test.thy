theory Composed_Function_Result_Test
  imports Rust_Base_Setup
begin

text \<open>
  In comp, the declaration result variable is instantiated by a function.
  Applying that returned function consumes additional arguments, so the expected
  final list value is not the representation of the whole result variable.
  Argument adapters must retain its function prefix and emit no call on a list.
  The direct and constructor-wrapped forms are controls. Passing the value to
  retain_list supplies an explicit expected argument type and exposes the bug.
\<close>

definition composed_map :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a list list \<Rightarrow> 'b list list"
  where "composed_map f xss = (map \<circ> map) f xss"

definition composed_wrapped :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a list list \<Rightarrow> 'b list list option"
  where "composed_wrapped f xss = Some ((map \<circ> map) f xss)"

definition retain_list :: "'a list \<Rightarrow> 'a list"
  where "retain_list xs = xs"

definition composed_forward :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a list list \<Rightarrow> 'b list list"
  where "composed_forward f xss = retain_list ((map \<circ> map) f xss)"

lemma composed_map_value: "composed_map f xss = map (map f) xss"
  by (simp add: composed_map_def)
lemma composed_wrapped_value: "composed_wrapped f xss = Some (map (map f) xss)"
  by (simp add: composed_wrapped_def)

lemma composed_forward_value: "composed_forward f xss = map (map f) xss"
  by (simp add: composed_forward_def retain_list_def)

export_code composed_map composed_wrapped composed_forward in Rust module_name ComposedFunctionResult

end
