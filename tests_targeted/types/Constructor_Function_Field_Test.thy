theory Constructor_Function_Field_Test
  imports Rust_Base_Setup
begin

text \<open>
  A datatype field keeps the arrows written in its declaration separate from
  arrows introduced by instantiating a result variable. For example a field
  's \<Rightarrow> 'a \<Rightarrow> 's becomes a two-argument Rust callback returning
  another callback when 's is a function type. Constructor applications must
  honor this layout even without an enclosing expression's expected type.
  These three constructions cover the function-state setter, a getter with a
  function-valued result, and a binary operation on functions.
\<close>

datatype ('a, 's) field_lens =
  FieldLens "'s \<Rightarrow> 'a" "'s \<Rightarrow> 'a \<Rightarrow> 's"

definition function_field_lens :: "'k::equal \<Rightarrow> ('v, 'k \<Rightarrow> 'v) field_lens"
  where "function_field_lens k = FieldLens (\<lambda>f. f k) (\<lambda>f v. f(k := v))"

definition bool_function_field_lens :: "bool \<Rightarrow> (bool, bool \<Rightarrow> bool) field_lens"
  where "bool_function_field_lens k = function_field_lens k"

datatype ('a, 'b) output_field = OutputField "'a \<Rightarrow> 'b"

definition returning_function_field :: "(bool, bool \<Rightarrow> bool) output_field"
  where "returning_function_field = OutputField (\<lambda>x y. x \<noteq> y)"

datatype 'a operation_field = OperationField "'a \<Rightarrow> 'a \<Rightarrow> 'a"

definition function_operation_field :: "(bool \<Rightarrow> bool) operation_field"
  where "function_operation_field =
    OperationField (\<lambda>f g x. if x then g x else f x)"

text \<open>
  Observe fields through generated HOL pattern matching as well as from the
  Rust runtime test. The specialized setter's returned function must keep its
  own call boundary when it is bound by the constructor pattern.
\<close>
definition apply_field_lens ::
  "bool \<Rightarrow> (bool \<Rightarrow> bool) \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool \<times> bool"
  where "apply_field_lens k f v x =
    (case bool_function_field_lens k of FieldLens get put \<Rightarrow> (get f, put f v x))"

definition apply_output_field ::
  "(bool, bool \<Rightarrow> bool) output_field \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool"
  where "apply_output_field box x y = (case box of OutputField f \<Rightarrow> f x y)"

definition apply_operation_field ::
  "(bool \<Rightarrow> bool) operation_field \<Rightarrow>
   (bool \<Rightarrow> bool) \<Rightarrow> (bool \<Rightarrow> bool) \<Rightarrow> bool \<Rightarrow> bool"
  where "apply_operation_field box f g x =
    (case box of OperationField combine \<Rightarrow> combine f g x)"

lemma application_observations:
  "apply_field_lens k f v x = (f k, if x = k then v else f x)"
  "apply_output_field returning_function_field x y = (x \<noteq> y)"
  "apply_operation_field function_operation_field f g x = (if x then g x else f x)"
  by (simp_all add: apply_field_lens_def apply_output_field_def
      apply_operation_field_def bool_function_field_lens_def function_field_lens_def
      returning_function_field_def function_operation_field_def)

lemma field_lens_observation:
  "case bool_function_field_lens k of FieldLens get put \<Rightarrow>
    get f = f k \<and> put f v x = (if x = k then v else f x)"
  by (simp add: bool_function_field_lens_def function_field_lens_def)

lemma returning_field_observation:
  "case returning_function_field of OutputField f \<Rightarrow> f x y = (x \<noteq> y)"
  by (simp add: returning_function_field_def)

lemma operation_field_observation:
  "case function_operation_field of OperationField combine \<Rightarrow>
    combine f g x = (if x then g x else f x)"
  by (simp add: function_operation_field_def)

export_code function_field_lens bool_function_field_lens
  returning_function_field function_operation_field
  apply_field_lens apply_output_field apply_operation_field
  in Rust module_name ConstructorFunctionField

end
