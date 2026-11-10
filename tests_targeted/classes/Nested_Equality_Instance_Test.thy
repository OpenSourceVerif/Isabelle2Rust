theory Nested_Equality_Instance_Test
  imports Rust_Base_Setup
begin

text \<open>
  A nested recursive datatype needs its generated equality instance when it
  is passed to a polymorphic equality operation. Both the term and list
  equality implementations must be retained, including their recursive calls.
  The function and variable labels are separate type parameters.
\<close>

datatype ('f, 'v) equality_term =
    EVar 'v
  | EFun 'f "(('f, 'v) equality_term) list"

definition compare_values :: "'a::equal \<Rightarrow> 'a \<Rightarrow> bool"
  where "compare_values x y = (x = y)"

definition compare_terms ::
  "('f::equal, 'v::equal) equality_term \<Rightarrow> ('f, 'v) equality_term \<Rightarrow> bool"
  where "compare_terms x y = compare_values x y"

definition compare_bool_terms ::
  "(bool, bool) equality_term \<Rightarrow> (bool, bool) equality_term \<Rightarrow> bool"
  where "compare_bool_terms x y = compare_terms x y"

export_code compare_values compare_terms compare_bool_terms in Rust module_name NestedEqualityInstance

end
