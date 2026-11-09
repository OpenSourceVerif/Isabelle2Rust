theory Generic_Type_Name_Test
  imports Rust_Base_Setup
begin

text \<open>
  Rust nominal types and traits must not be shadowed by generated generic
  parameter names. The abstract seven-parameter g reproduces BNF_CC's
  struct G<A,B,C,D,E,F,G> derive failure. The recursive a also checks type
  references and constructor patterns, while class b checks generic bounds.
  Class t additionally collides with the fixed T in blanket marker impls.
  All exported declarations and uses must share the same fresh nominal names.
\<close>

typedecl ('a, 'b, 'c, 'd, 'e, 'f, 'g) g

definition abstract_identity ::
  "('a, 'b, 'c, 'd, 'e, 'f, 'g) g \<Rightarrow> ('a, 'b, 'c, 'd, 'e, 'f, 'g) g"
  where "abstract_identity x = x"

datatype 'a a = ALeaf 'a | ABranch "'a a"

fun tree_map :: "('a \<Rightarrow> 'b) \<Rightarrow> 'a a \<Rightarrow> 'b a"
  where "tree_map f (ALeaf x) = ALeaf (f x)"
  | "tree_map f (ABranch t) = ABranch (tree_map f t)"

class b =
  fixes observe_b :: "'a \<Rightarrow> bool"

definition observe_pair :: "'a \<Rightarrow> 'b::b \<Rightarrow> 'a \<times> bool"
  where "observe_pair x y = (x, observe_b y)"

class t = b

definition observe_marker :: "'a::t \<Rightarrow> bool"
  where "observe_marker x = observe_b x"

export_code abstract_identity tree_map observe_pair observe_marker
  in Rust module_name GenericNames

end
