theory Model imports AlgebraicStructure_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (case AlgebraicStructure_Test.mapsome (\<lambda>x::nat. x+List.length input) (if hd (input@[0])=0 then None else Some (hd (input@[0])-1)) of None \<Rightarrow> [0] | Some n \<Rightarrow> [1,n])"
end
