theory Variables_Test
  imports Main "Rust.Rust_Setup"
begin

fun param_id :: "'a \<Rightarrow> 'a" where
  "param_id x = x"

definition rust_keyword :: "int \<Rightarrow> int" where
  "rust_keyword loop = loop"

definition case_var :: "'a \<Rightarrow> 'a" where
  "case_var x = (case x of y \<Rightarrow> y)"

definition lambda_var :: "int \<Rightarrow> int" where
  "lambda_var x = (\<lambda>y. x) x"

definition pair_second :: "'a \<times> 'b \<Rightarrow> 'b" where
  "pair_second p = (case p of (_, y) \<Rightarrow> y)"

definition ignore_arg :: "'a \<Rightarrow> int" where
  "ignore_arg x = (case x of _ \<Rightarrow> 0)"

definition shadowed_case :: "'a \<Rightarrow> 'a \<times> 'a" where
  "shadowed_case x = (case x of y \<Rightarrow> (let x = y in (x, y)))"

export_code
  param_id rust_keyword case_var lambda_var pair_second ignore_arg shadowed_case
  in Rust

end
