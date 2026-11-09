theory Conditional_Operand_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  HOL conditionals can be operands of arithmetic expressions. A Rust if used
  as the left operand at a statement boundary needs parentheses, otherwise
  rustc parses its closing brace as the end of a statement. Cover both operand
  sides, multiplication, comparison, and nested conditionals.
\<close>

definition conditional_sum :: "bool \<Rightarrow> bool \<Rightarrow> integer"
  where "conditional_sum b c = (if b then 2 else 3) + (if c then 5 else 7)"
definition conditional_product :: "bool \<Rightarrow> integer \<Rightarrow> integer"
  where "conditional_product b x = (if b then x else -x) * x"
definition conditional_compare :: "bool \<Rightarrow> bool \<Rightarrow> bool"
  where "conditional_compare b c = ((if b then (if c then 11 else 13) else 17) < (19 :: integer))"

export_code conditional_sum conditional_product conditional_compare in Rust

end
