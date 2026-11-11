theory Model imports AlgebraicStructure_Test begin

definition dec :: "nat \<Rightarrow> int" where "dec n = (if n mod 2 = 1 then - int (Suc (n div 2)) else int (n div 2))"
definition enc :: "int \<Rightarrow> nat" where "enc z = (if z < 0 then 2 * nat (-z) - 1 else 2 * nat z)"
(* Exact wire conversion avoids an incomplete generic int Ord instance in the
   existing Rust serializer. Isabelle checks this observation-only equation. *)
declare enc_def[code del]
lemma enc_integer_wire [code]:
 "enc z = (if z < 0 then 2 * nat_of_integer (integer_of_int (-z)) - 1 else 2 * nat_of_integer (integer_of_int z))"
 by (simp add: enc_def nat_of_integer.rep_eq)


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (case AlgebraicStructure_Test.comps (if hd(input@[0])=0 then None else Some(dec(hd(input@[0])-1))) of None \<Rightarrow> [0] | Some n \<Rightarrow> [1,enc n])"
end
