theory Mapped_Result_Shape_Test
  imports Rust_Base_Setup
begin

text \<open>
  An annotation for a registered result uses the same representation as its
  contextual arguments. In particular, an adapted tuple must not erase the
  nested function groups selected by the surrounding equality dictionary.
\<close>

definition mapped_shape_pair :: "'a \<Rightarrow> 'b \<Rightarrow> 'a \<times> 'b"
  where "mapped_shape_pair a b = (a, b)"

code_printing constant mapped_shape_pair \<rightharpoonup> (Rust) "!(_, _)"

definition equal_mapped_pair ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow>
   (bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool"
  where "equal_mapped_pair f g = HOL.equal (mapped_shape_pair f True) (g, True)"

definition observe_plain_mapped_pair ::
  "(bool \<Rightarrow> bool \<Rightarrow> bool) \<Rightarrow> bool \<Rightarrow> bool"
  where "observe_plain_mapped_pair f b =
    (case mapped_shape_pair f b of (g, c) \<Rightarrow> g c c)"

lemma mapped_shape_observations:
  "equal_mapped_pair f g = (f = g)"
  "observe_plain_mapped_pair f b = f b b"
  by (simp_all add: equal_mapped_pair_def observe_plain_mapped_pair_def
      mapped_shape_pair_def equal_eq)

export_code equal_mapped_pair observe_plain_mapped_pair
  in Rust module_name MappedResultShape

end
