theory Dictionary_Result_Application_Test
  imports Rust_Base_Setup
begin

text \<open>
  A plain polymorphic function may return a type variable whose function
  representation is selected by its class dictionary. For a function instance
  of bot, that result uses recursively unary Rust Fn objects, even when the
  same HOL arrows are normally flattened. Calls after the ordinary function
  must consume the dictionary-selected groups, consistently with its argument
  adaptation. Cover fully applied, returned, ternary, and higher-order results,
  with an unconstrained wrapper as a control for the ordinary flat layout.
\<close>

definition dictionary_pick :: "bool \<Rightarrow> 'a::bot \<Rightarrow> 'a"
  where "dictionary_pick b x = (if b then x else bot)"

definition flat_pick :: "bool \<Rightarrow> 'a \<Rightarrow> 'a \<Rightarrow> 'a"
  where "flat_pick b x y = (if b then x else y)"

definition dictionary_apply :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool"
  where "dictionary_apply b x y = dictionary_pick b (\<lambda>p q. p \<and> q) x y"

definition dictionary_value :: "bool \<Rightarrow> (bool \<Rightarrow> bool \<Rightarrow> bool)"
  where "dictionary_value b = dictionary_pick b (\<lambda>p q. p \<or> q)"

definition dictionary_three :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool"
  where "dictionary_three b x y z =
    dictionary_pick b (\<lambda>p q r. (p \<noteq> q) \<and> r) x y z"

definition dictionary_higher :: "bool \<Rightarrow> (bool \<Rightarrow> bool) \<Rightarrow> bool \<Rightarrow> bool"
  where "dictionary_higher b f x = dictionary_pick b (\<lambda>g p. g p) f x"

definition dictionary_flat_control :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool"
  where "dictionary_flat_control b x y =
    flat_pick b (\<lambda>p q. p \<and> q) (\<lambda>p q. p \<or> q) x y"

export_code dictionary_apply dictionary_value dictionary_three dictionary_higher
  dictionary_flat_control in Rust module_name DictionaryResult

end
