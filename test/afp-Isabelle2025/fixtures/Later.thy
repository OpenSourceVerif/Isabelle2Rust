theory Later
  imports Origin
begin

(* A later code declaration must be discovered under Origin.thy, where the
   constant was introduced, even though Origin alone has no code certificate. *)
declare late_equation_def[code]

definition ordinary :: bool where "ordinary = True"

end
