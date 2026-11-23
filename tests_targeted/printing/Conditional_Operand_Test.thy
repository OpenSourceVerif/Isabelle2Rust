theory Conditional_Operand_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  Rust conditionals need grouping in operand positions but not in function
  arguments or tail positions. Cover both arithmetic operand sides, the
  multiplication statement-boundary ambiguity, comparison, boolean operands,
  and nested tail conditionals.
\<close>

definition conditional_tail :: "bool \<Rightarrow> bool \<Rightarrow> integer"
  where "conditional_tail b c = (if b then (if c then 11 else 13) else 17)"
definition conditional_sum :: "bool \<Rightarrow> bool \<Rightarrow> integer"
  where "conditional_sum b c = (if b then 2 else 3) + (if c then 5 else 7)"
definition conditional_product :: "bool \<Rightarrow> integer \<Rightarrow> integer"
  where "conditional_product b x = (if b then x else -x) * x"
definition conditional_compare :: "bool \<Rightarrow> bool \<Rightarrow> bool"
  where "conditional_compare b c = ((if b then (if c then 11 else 13) else 17) < (13 :: integer))"
definition conditional_and :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool"
  where "conditional_and b c d = ((if b then c else \<not> c) \<and> d)"
definition conditional_or :: "bool \<Rightarrow> bool \<Rightarrow> bool \<Rightarrow> bool"
  where "conditional_or b c d = (d \<or> (if b then c else \<not> c))"
definition conditional_argument :: "bool \<Rightarrow> bool \<Rightarrow> integer"
  where "conditional_argument b c = conditional_sum (if b then c else \<not> c) c"
definition conditional_condition :: "bool \<Rightarrow> bool \<Rightarrow> integer"
  where "conditional_condition b c = (if (if b then c else \<not> c) then 11 else 17)"

text \<open>
  A custom syntax printer supplies only fixity for its holes. NOBR does not
  guarantee that a hole is delimited: this printer follows it with an operator.
\<close>

definition opaque_bool :: "bool \<Rightarrow> bool"
  where "opaque_bool b = b"

setup \<open>
  Code_Target.set_printings (Code_Symbol.Constant
    (\<^const_name>\<open>opaque_bool\<close>,
      [(Code_Rust.target, SOME (Code_Printer.simple_const_syntax
        (1, fn print => fn _ => fn [(t, _)] =>
          Pretty.block [print Code_Printer.NOBR t, Pretty.str " && true"]
        | _ => error "opaque_bool expects one argument")))]))
\<close>

definition conditional_opaque :: "bool \<Rightarrow> bool \<Rightarrow> bool"
  where "conditional_opaque b c = opaque_bool (if b then c else \<not> c)"

export_code conditional_tail conditional_sum conditional_product conditional_compare
  conditional_and conditional_or conditional_argument conditional_condition
  conditional_opaque in Rust

end
