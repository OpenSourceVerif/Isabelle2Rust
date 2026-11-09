theory Rust2024_Keywords_Test
  imports Rust_Base_Setup
begin

text \<open>
  HOL identifiers may be Rust 2024 reserved words. Both item names and local
  binders must be renamed consistently at declarations and uses. Before the
  fix, gen (and the older async/await/dyn keywords) emitted invalid Rust.
\<close>

definition gen :: "bool \<Rightarrow> bool" where "gen = (\<lambda>gen. \<not> gen)"
definition async :: "bool \<Rightarrow> bool" where "async = (\<lambda>await. gen await)"
definition await :: "bool \<Rightarrow> bool" where "await = (\<lambda>dyn. async dyn)"
definition dyn :: "bool \<Rightarrow> bool" where "dyn = (\<lambda>gen. await gen)"

export_code gen async await dyn in Rust

end
