theory Mapped_Arithmetic_Instance_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  Native zero, addition, and multiplication must remain available as dictionary
  methods after code_printing removes their specialized function nodes. These
  operations agree across the existing BigInt representations of integer, int,
  and nat. No subtraction instance or numeric representation is changed here.
\<close>

definition arithmetic_result ::
  "'a::semiring_1 \<Rightarrow> 'a \<Rightarrow> nat \<Rightarrow> 'a \<times> 'a \<times> 'a \<times> 'a \<times> 'a"
  where "arithmetic_result x y n = (sum_list [], sum_list [x, y, x], x * y, x ^ n, 37)"

definition integer_arithmetic ::
  "integer \<Rightarrow> integer \<Rightarrow> nat \<Rightarrow> integer \<times> integer \<times> integer \<times> integer \<times> integer"
  where "integer_arithmetic x y n = arithmetic_result x y n"

definition nat_arithmetic ::
  "nat \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> nat \<times> nat \<times> nat \<times> nat \<times> nat"
  where "nat_arithmetic x y n = arithmetic_result x y n"

definition int_arithmetic ::
  "int \<Rightarrow> int \<Rightarrow> nat \<Rightarrow> int \<times> int \<times> int \<times> int \<times> int"
  where "int_arithmetic x y n = arithmetic_result x y n"

lemma arithmetic_observations:
  "integer_arithmetic (-3) 2 2 = (0, -4, -6, 9, 37)"
  "nat_arithmetic 3 2 3 = (0, 8, 6, 27, 37)"
  "int_arithmetic (-3) 2 2 = (0, -4, -6, 9, 37)"
  by (simp_all add: integer_arithmetic_def nat_arithmetic_def int_arithmetic_def arithmetic_result_def)

export_code integer_arithmetic in Rust module_name MappedArithmetic
export_code nat_arithmetic in Rust module_name MappedArithmetic
export_code integer_arithmetic nat_arithmetic int_arithmetic in Rust module_name MappedArithmetic
export_code integer_arithmetic nat_arithmetic int_arithmetic in Rust

end
