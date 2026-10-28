theory Origin
  imports Main
begin

(* The defining theory intentionally has no code equations for these constants.
   Later restores the first equation; the second must remain outside the scope. *)
definition late_equation :: nat where "late_equation = 7"
declare late_equation_def[code del]

definition no_equation :: nat where "no_equation = 11"
declare no_equation_def[code del]

(* An abbreviation has namespace provenance but is not an executable constant. *)
abbreviation not_a_constant :: nat where "not_a_constant \<equiv> 3"

end
