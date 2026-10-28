theory Hidden_Constant
  imports Main
begin

(* Fully hiding a constant removes external name access, including its qualified
   spelling, but retains its internal declaration and executable code equation.
   A scanner's internal Const name must therefore reach the code generator
   without being read again as a surface-syntax term. *)
definition hidden_not :: "bool \<Rightarrow> bool"
  where "hidden_not b = (\<not> b)"

hide_const hidden_not

end
