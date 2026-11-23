theory Empty_Case_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  Thingol removes case branches whose body is the undefined constant. If all
  branches are removed, the Rust backend must emit one well-formed diverging
  expression. The result must type-check both directly and inside a boxed list
  field, including a polymorphic result. A native integer addition also needs
  the contextual operand type on this diverging expression. A stored callback
  must only fail when
  called, and a safe conditional branch must remain executable. These checks
  exercise the backend's existing failure convention for undefined code; they
  do not assign a HOL value to undefined. A partially applied function-valued
  empty case must retain its arrows so the existing eta wrapper supplies the
  missing argument instead of emitting an underapplied Rust call.
\<close>

definition empty_case_value :: "bool option \<Rightarrow> bool" where
  "empty_case_value x =
    (case x of None \<Rightarrow> undefined | Some b \<Rightarrow> undefined)"

definition empty_case_generic :: "'a option \<Rightarrow> 'b option" where
  "empty_case_generic x =
    (case x of None \<Rightarrow> undefined | Some a \<Rightarrow> undefined)"

definition empty_case_field :: "bool option \<Rightarrow> bool list" where
  "empty_case_field x = False #
    (case x of None \<Rightarrow> undefined | Some b \<Rightarrow> undefined)"

datatype empty_callback = EmptyCallback "bool option \<Rightarrow> bool"

definition empty_case_callback :: "bool \<Rightarrow> empty_callback" where
  "empty_case_callback enabled =
    EmptyCallback (if enabled then empty_case_value else (\<lambda>_. False))"

definition safe_empty_case :: "bool \<Rightarrow> bool option \<Rightarrow> bool" where
  "safe_empty_case enabled x = (if enabled then empty_case_value x else True)"

definition empty_case_operand :: "bool \<Rightarrow> bool option \<Rightarrow> bool" where
  "empty_case_operand enabled x = (enabled \<and>
    (case x of None \<Rightarrow> undefined | Some b \<Rightarrow> undefined))"

definition empty_case_integer :: "bool option \<Rightarrow> integer" where
  "empty_case_integer x =
    (case x of None \<Rightarrow> undefined | Some b \<Rightarrow> undefined) + 1"

definition partial_empty_case ::
  "bool option \<Rightarrow> bool \<Rightarrow> empty_callback" where
  "partial_empty_case x b =
    EmptyCallback ((case x of None \<Rightarrow> undefined | Some c \<Rightarrow> undefined) b)"

lemma empty_case_operand_disabled: "empty_case_operand False x = False"
  by (simp add: empty_case_operand_def)

lemma safe_empty_case_disabled: "safe_empty_case False x = True"
  by (simp add: safe_empty_case_def)

export_code empty_case_value empty_case_generic empty_case_field
  empty_case_callback safe_empty_case empty_case_operand empty_case_integer partial_empty_case in Rust module_name EmptyCase

end
