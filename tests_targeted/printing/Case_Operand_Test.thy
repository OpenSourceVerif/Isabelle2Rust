theory Case_Operand_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  HOL cases can occur as operands of boolean and arithmetic expressions.
  Rust must parse the entire match or irrefutable binding block as an
  expression before the following operator, including at a function or match
  arm boundary. Exercise ordinary cases, both operand sides, nested cases,
  a single product pattern, and nested boxed patterns lowered by the stable
  pattern-matrix compiler.
\<close>

datatype operand_choice = Take bool | Skip
datatype operand_pair = Pair bool bool
datatype operand_tree = Leaf bool | Branch operand_tree operand_tree

definition case_and :: "operand_choice \<Rightarrow> bool \<Rightarrow> bool"
  where "case_and c b = ((case c of Take x \<Rightarrow> x | Skip \<Rightarrow> True) \<and> b)"

definition case_or :: "operand_choice \<Rightarrow> bool \<Rightarrow> bool"
  where "case_or c b = ((case c of Take x \<Rightarrow> x | Skip \<Rightarrow> False) \<or> b)"

definition case_right :: "operand_choice \<Rightarrow> bool \<Rightarrow> bool"
  where "case_right c b = (b \<and> (case c of Take x \<Rightarrow> x | Skip \<Rightarrow> True))"

definition case_nested :: "operand_choice \<Rightarrow> operand_choice \<Rightarrow> bool \<Rightarrow> bool"
  where "case_nested c d b =
    ((case c of Take x \<Rightarrow> (case d of Take y \<Rightarrow> y | Skip \<Rightarrow> True) \<and> x
      | Skip \<Rightarrow> b) \<or> b)"

definition case_arithmetic :: "operand_choice \<Rightarrow> integer \<Rightarrow> integer"
  where "case_arithmetic c k =
    (case c of Take x \<Rightarrow> (if x then 2 else 5) | Skip \<Rightarrow> -3) + k"

definition case_pair :: "(bool \<times> bool) \<Rightarrow> bool \<Rightarrow> bool"
  where "case_pair p b = ((case p of (x,y) \<Rightarrow> x \<or> y) \<and> b)"

definition case_binding :: "operand_pair \<Rightarrow> bool \<Rightarrow> bool"
  where "case_binding p b = ((case p of Pair x y \<Rightarrow> x \<or> y) \<and> b)"

definition case_tree :: "operand_tree \<Rightarrow> bool \<Rightarrow> bool"
  where "case_tree t b =
    ((case t of Branch (Leaf x) (Leaf y) \<Rightarrow> x \<and> y
      | Leaf x \<Rightarrow> x | _ \<Rightarrow> False) \<and> b)"

export_code case_and case_or case_right case_nested case_arithmetic case_pair case_binding case_tree
  in Rust module_name CaseOperand

end
