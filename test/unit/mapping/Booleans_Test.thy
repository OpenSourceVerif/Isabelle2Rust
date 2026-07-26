theory Booleans_Test
  imports Main "Rust.Rust_Base_Setup"
begin

(* Rust_Base_Setup maps HOL bools, connectives, and conditionals to Rust bool code. *)

definition bool_not :: "bool \<Rightarrow> bool" where
  "bool_not b = (\<not> b)"

definition bool_and_or :: "bool \<Rightarrow> bool \<Rightarrow> bool" where
  "bool_and_or p q = ((p \<and> \<not> q) \<or> (q \<and> \<not> p))"

definition bool_if :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool" where
  "bool_if c x y = (if c then x else y)"

definition bool_nested :: "bool \<Rightarrow> bool \<Rightarrow> bool" where
  "bool_nested p q = (if p \<and> q then True else p \<or> q)"

export_code
  bool_not bool_and_or bool_if bool_nested
  in Rust

end
