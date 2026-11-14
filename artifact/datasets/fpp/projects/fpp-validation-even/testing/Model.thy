theory Model imports Recursion_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [if Recursion_Test.even (input!0) then 1 else 0]"
end
