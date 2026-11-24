theory Catalogue_Coverage
  imports Main
begin

(* A plain logical constant can be supplied by a target printing rather than
   by registered code equations. This fixture only produces source text. *)
consts target_only :: "nat \<Rightarrow> nat"
code_printing constant target_only \<rightharpoonup> (SML) "(fn x => x)"

definition target_wrapper :: "nat \<Rightarrow> nat" where "target_wrapper n = target_only n"

datatype token = Token

(* An explicit aborting function has an empty code-equation specification. *)
consts abort_only :: "nat \<Rightarrow> nat"
setup \<open>Code.declare_aborting_global \<^const_name>\<open>abort_only\<close>\<close>

(* Ordinary definitions and locale interpretations establish provenance. *)
definition ordinary :: "bool \<Rightarrow> bool" where "ordinary b = (\<not> b)"
locale audit_locale = fixes n :: nat
begin
definition local_plus :: "nat \<Rightarrow> nat" where "local_plus x = x + n"
end
interpretation audit_instance: audit_locale "2" .

(* Abstract equations and their projection are both executable ingredients. *)
typedef wrapped = "UNIV :: nat list set" morphisms unwrap Wrap by simp
declare unwrap_inverse [code abstype]
definition wrapped_empty :: wrapped where "wrapped_empty = Wrap []"
lemma wrapped_empty_code [code abstract]: "unwrap wrapped_empty = []"
  by (simp add: wrapped_empty_def Wrap_inverse)

(* Frozen discovery keeps declarations even with no equations and preserves
   internal namespace provenance after surface lookup has been disabled. *)
definition no_equation :: nat where "no_equation = 11"
declare no_equation_def[code del]
abbreviation not_a_constant :: nat where "not_a_constant \<equiv> 3"
definition hidden :: bool where "hidden = True"
hide_const hidden

end
