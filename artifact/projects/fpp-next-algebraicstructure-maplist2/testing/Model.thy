theory Model imports AlgebraicStructure_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = AlgebraicStructure_Test.maplist2 (\<lambda>x::nat. x+List.length input) input"
end
