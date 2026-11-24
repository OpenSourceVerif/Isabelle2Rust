theory Branch_Left
  imports Branch_Base
begin

(* The left branch supplies an executable equation for the shared declaration.
   Discovery must retain this instance and left_marker when the full merge
   fails, together with equations inherited from other compatible branches. *)
instantiation bool :: branch_value
begin

definition branch_choice_bool :: "bool \<Rightarrow> nat"
  where "branch_choice_bool _ = 1"

instance ..

end

definition left_marker :: bool where "left_marker = True"

end
