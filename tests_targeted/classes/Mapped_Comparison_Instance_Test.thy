theory Mapped_Comparison_Instance_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  Code-printing removes native comparison implementations from the emitted
  function graph, but their class dictionaries are still needed by ordinary
  polymorphic calls. Integer-only and nat-only exports must work independently;
  a mixed export must not require duplicate impls for the shared BigInt type.
  These observations use only equality and order, whose existing native
  mappings agree across integer, int, and nat. Arithmetic instances are separate.
\<close>

definition comparison_result ::
  "'a::{equal,ord} \<Rightarrow> 'a \<Rightarrow> bool \<times> bool \<times> bool \<times> 'a \<times> 'a"
  where "comparison_result x y = (List.member [y] x, x < y, x \<le> y, min x y, max x y)"

definition integer_comparison ::
  "integer \<Rightarrow> integer \<Rightarrow> bool \<times> bool \<times> bool \<times> integer \<times> integer"
  where "integer_comparison = comparison_result"

definition nat_comparison ::
  "nat \<Rightarrow> nat \<Rightarrow> bool \<times> bool \<times> bool \<times> nat \<times> nat"
  where "nat_comparison = comparison_result"

definition int_comparison ::
  "int \<Rightarrow> int \<Rightarrow> bool \<times> bool \<times> bool \<times> int \<times> int"
  where "int_comparison = comparison_result"

lemma comparison_observations:
  "integer_comparison 1 2 = (False, True, True, 1, 2)"
  "nat_comparison 1 2 = (False, True, True, 1, 2)"
  "int_comparison (-2) (-1) = (False, True, True, -2, -1)"
  by (simp_all add: integer_comparison_def nat_comparison_def int_comparison_def
      comparison_result_def List.member_def min_def max_def)

export_code integer_comparison in Rust module_name MappedComparison
export_code nat_comparison in Rust module_name MappedComparison
export_code integer_comparison nat_comparison int_comparison in Rust module_name MappedComparison

export_code integer_comparison nat_comparison int_comparison in Rust

end
