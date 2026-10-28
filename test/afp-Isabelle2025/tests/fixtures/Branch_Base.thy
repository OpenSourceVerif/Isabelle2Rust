theory Branch_Base
  imports Main
begin

(* Separate theory branches may define this common declaration differently.
   Neither branch imports the other; their loaded contexts remain valid even
   though importing both into a new theory would clash. *)
class branch_value =
  fixes branch_choice :: "'a \<Rightarrow> nat"

end
