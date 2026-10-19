theory Branch_Right
  imports Branch_Base
begin

(* This independent branch intentionally conflicts with the left specification.
   Its own executable constant must still be discovered in its valid context. *)
instantiation bool :: branch_value
begin

definition branch_choice_bool :: "bool \<Rightarrow> nat"
  where "branch_choice_bool _ = 2"

instance ..

end

definition right_marker :: bool where "right_marker = False"

end
