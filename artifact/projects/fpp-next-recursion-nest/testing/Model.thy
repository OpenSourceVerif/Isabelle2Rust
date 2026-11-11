theory Model imports Recursion_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [Recursion_Test.nest (input!0)]"
end
