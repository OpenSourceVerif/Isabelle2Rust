theory Code_Context
  imports Main "HOL-Library.Code_Target_Numeral"
begin

(* A numeral in a registered code pattern must be normalized by code_unfold
   rules to the integer code constructors (zero_integer, Pos and Neg).
   Ordinary HOL simp rules leave one_integer at this pattern position, although
   it is not a code constructor. The scanner must retain this equation without
   reporting the ordinary-simpset failure as a code-generator rejection. *)
definition integer_one :: "integer \<Rightarrow> bool"
  where "integer_one n = (n = 1)"

declare integer_one_def [code del]

lemma integer_one_literal [code]: "integer_one (1 :: integer) = True"
  by (simp add: integer_one_def)

end
