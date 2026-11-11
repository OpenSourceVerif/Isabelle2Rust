theory Model imports Recursion_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [if Recursion_Test.len2 input then 1 else 0]"
end
