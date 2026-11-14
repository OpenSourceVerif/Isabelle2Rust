theory Model imports AlgebraicStructure_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = AlgebraicStructure_Test.sqr_even input"
end
