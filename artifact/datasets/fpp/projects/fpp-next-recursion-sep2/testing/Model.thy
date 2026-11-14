theory Model imports Recursion_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Recursion_Test.sep2 input (List.length input)"
end
