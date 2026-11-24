theory Case_Operand_Test
  imports Rust_BigInt_Setup
begin

text \<open>
  HOL cases can occur as operands of boolean and arithmetic expressions.
  Rust must parse the entire match or irrefutable binding block as an
  expression before the following operator, including at a function or match
  arm boundary. Exercise ordinary cases, both operand sides, nested cases,
  a single product pattern, and nested boxed patterns lowered by the stable
  pattern-matrix compiler. Tail positions and function arguments do not need
  parentheses around matches or irrefutable binding blocks.
\<close>

datatype operand_choice = Take bool | Skip
datatype operand_pair = Pair bool bool
datatype operand_tree = Leaf bool | Branch operand_tree operand_tree

definition case_tail :: "operand_choice \<Rightarrow> bool"
  where "case_tail c = (case c of Take x \<Rightarrow> x | Skip \<Rightarrow> False)"

definition case_and :: "operand_choice \<Rightarrow> bool \<Rightarrow> bool"
  where "case_and c b = ((case c of Take x \<Rightarrow> x | Skip \<Rightarrow> True) \<and> b)"

definition case_or :: "operand_choice \<Rightarrow> bool \<Rightarrow> bool"
  where "case_or c b = ((case c of Take x \<Rightarrow> x | Skip \<Rightarrow> False) \<or> b)"

definition case_right :: "operand_choice \<Rightarrow> bool \<Rightarrow> bool"
  where "case_right c b = (b \<and> (case c of Take x \<Rightarrow> x | Skip \<Rightarrow> True))"

definition case_argument :: "operand_choice \<Rightarrow> bool \<Rightarrow> bool"
  where "case_argument c b = case_and c (case c of Take x \<Rightarrow> x | Skip \<Rightarrow> b)"

definition case_condition :: "operand_choice \<Rightarrow> integer"
  where "case_condition c = (if (case c of Take x \<Rightarrow> x | Skip \<Rightarrow> False) then 11 else 17)"

definition case_callee :: "operand_choice \<Rightarrow> bool \<Rightarrow> bool"
  where "case_callee c b = (case c of Take x \<Rightarrow> (\<lambda>a. x \<and> a) | Skip \<Rightarrow> (\<lambda>a. \<not> a)) b"

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

definition case_binding_tail :: "operand_pair \<Rightarrow> bool"
  where "case_binding_tail p = (case p of Pair x y \<Rightarrow> x \<or> y)"

definition case_binding_argument :: "operand_pair \<Rightarrow> bool \<Rightarrow> bool"
  where "case_binding_argument p b = case_and (Take b) (case p of Pair x y \<Rightarrow> x \<or> y)"

definition case_binding_condition :: "operand_pair \<Rightarrow> integer"
  where "case_binding_condition p = (if (case p of Pair x y \<Rightarrow> x \<or> y) then 11 else 17)"

definition case_tree :: "operand_tree \<Rightarrow> bool \<Rightarrow> bool"
  where "case_tree t b =
    ((case t of Branch (Leaf x) (Leaf y) \<Rightarrow> x \<and> y
      | Leaf x \<Rightarrow> x | _ \<Rightarrow> False) \<and> b)"

definition case_boxed_if :: "bool \<Rightarrow> operand_tree \<Rightarrow> operand_tree \<Rightarrow> operand_tree"
  where "case_boxed_if b x y = Branch (if b then x else y) x"

export_code case_tail case_and case_or case_right case_argument case_condition case_callee
  case_nested case_arithmetic case_pair case_binding case_binding_tail
  case_binding_argument case_binding_condition case_tree case_boxed_if
  in Rust module_name CaseOperand

end
