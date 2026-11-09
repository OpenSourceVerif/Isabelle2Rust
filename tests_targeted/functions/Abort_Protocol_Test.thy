theory Abort_Protocol_Test
  imports Rust_Base_Setup
begin

text \<open>
  Code.abort consumes a String.literal message and a delayed fallback, then
  raises an error at any result type. The Rust adapter must preserve dynamic
  messages, leave the fallback unexecuted, and panic after both arguments have
  been supplied. Function-valued results must not become calls of a panic value;
  unapplied/partially applied aborts must remain first-class functions.
\<close>

definition abort_message :: String.literal where "abort_message = STR ''abort test''"
definition abort_bool :: "String.literal \<Rightarrow> bool \<Rightarrow> bool"
  where "abort_bool msg ok = (if ok then True else Code.abort msg (\<lambda>_. False))"
definition abort_result_function :: "String.literal \<Rightarrow> (bool \<Rightarrow> bool) option"
  where "abort_result_function msg = Some (Code.abort msg (\<lambda>_. id))"
definition abort_partial :: "String.literal \<Rightarrow> ((unit \<Rightarrow> bool) \<Rightarrow> bool) option"
  where "abort_partial msg = Some (Code.abort msg)"
definition abort_unapplied :: "(String.literal \<Rightarrow> (unit \<Rightarrow> bool) \<Rightarrow> bool) option"
  where "abort_unapplied = Some Code.abort"
definition abort_apply_function :: "String.literal \<Rightarrow> bool \<Rightarrow> bool"
  where "abort_apply_function msg x = Code.abort msg (\<lambda>_. id) x"

definition abort_operand :: "String.literal \<Rightarrow> bool \<Rightarrow> bool"
  where "abort_operand msg x = (Code.abort msg (\<lambda>_. True) \<and> x)"

export_code abort_operand abort_message abort_bool abort_result_function abort_partial
  abort_unapplied abort_apply_function in Rust module_name AbortProtocol

end
