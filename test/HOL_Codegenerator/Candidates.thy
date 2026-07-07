(* Author: Florian Haftmann, TU Muenchen *)

section \<open>A huge collection of equations to generate Rust code from\<close>

theory Candidates
imports
  Complex_Main
  "HOL-Library.Library"
  "HOL-Library.Sorting_Algorithms"
  "HOL-Library.Subseq_Order"
  "HOL-Library.RBT"
  "HOL-Data_Structures.Tree_Map"
  "HOL-Data_Structures.Tree_Set"
  "HOL-Computational_Algebra.Computational_Algebra"
  "HOL-Computational_Algebra.Polynomial_Factorial"
  "HOL-Number_Theory.Eratosthenes"
  "HOL-Examples.Records"
  "HOL-Examples.Gauss_Numbers"
begin

text \<open>
  Shared HOL-Codegenerator stress candidates for Rust.  This mirrors the
  Isabelle and Go slow-test candidate set: the imported theories expose many
  datatypes, classes, arithmetic definitions, data structures and code equations
  to \<^text>\<open>export_code\<close>, while the target-specific setup stays in the
  generating theories.
\<close>

text \<open>
  Drop technical code equations from \<^theory>\<open>HOL.Quickcheck_Narrowing\<close>.
  Those \<^const>\<open>Quickcheck_Narrowing.partial_term_of\<close> instances are an
  implementation device for Haskell narrowing rather than ordinary HOL
  definitions to be translated by the Rust backend.
\<close>

setup \<open>
fn thy =>
let
  val tycos = Sign.logical_types thy;
  val consts = map_filter (try (curry (Axclass.param_of_inst thy)
    \<^const_name>\<open>Quickcheck_Narrowing.partial_term_of\<close>)) tycos;
in fold Code.declare_unimplemented_global consts thy end
\<close>

text \<open>
  Predicate-compiler smoke definition.  Exporting \<^const>\<open>sublist\<close> together
  with the rest of the candidate graph exercises generated predicate code over
  list constructors and recursive rules.
\<close>

inductive sublist :: "'a list \<Rightarrow> 'a list \<Rightarrow> bool"
where
  empty: "sublist [] xs"
| drop: "sublist ys xs \<Longrightarrow> sublist ys (x # xs)"
| take: "sublist ys xs \<Longrightarrow> sublist (x # ys) (x # xs)"

code_pred sublist .

text \<open>
  Avoid a common target identifier in generated SML names.  This is inherited
  from the upstream stress candidate theory; it is target-scoped and does not
  change the Rust translation.
\<close>

code_reserved (SML) upto

text \<open>
  List literal with an embedded \<^text>\<open>let\<close>.  Keeping this candidate in the
  shared export graph checks that target printers preserve expression
  precedence when list syntax and local bindings are combined.
\<close>

definition funny_list :: "bool list"
where
  "funny_list = [let b = True in b, False]"

definition funny_list' :: "bool list"
where
  "funny_list' = funny_list"

lemma [code]:
  "funny_list' = [True, False]"
  by (simp add: funny_list_def funny_list'_def)

definition check_list :: unit
where
  "check_list = (if funny_list = funny_list' then () else undefined)"

text \<open>
  List of higher-order functions.  This candidate exercises translation of HOL
  function values stored inside data structures; for Rust these become cloneable
  \<^verbatim>\<open>Rc<dyn Fn(..) -> ..>\<close> trait objects.
\<close>

definition funny_funs :: "(bool \<Rightarrow> bool) list \<Rightarrow> (bool \<Rightarrow> bool) list"
where
  "funny_funs fs = (\<lambda>x. x \<or> True) # (\<lambda>x. x \<or> False) # fs"

text \<open>
  String literal round-trip candidates.  These keep the standard HOL string
  conversion constants in the stress graph so that Rust string and character
  literal printing is checked together with list-like string representations.
\<close>

definition \<open>hello = ''Hello, world!''\<close>

definition \<open>hello2 = String.explode (String.implode hello)\<close>

definition \<open>which_hello \<longleftrightarrow> hello \<le> hello2\<close>

end
