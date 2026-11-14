theory Model imports Recursion_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [Recursion_Test.exp (input!0) (input!1)]"
end
