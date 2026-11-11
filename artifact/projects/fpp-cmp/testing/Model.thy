theory Model imports Cmp_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [case Cmp_Test.cmp (input!0) (input!1) of Cmp_Test.LT \<Rightarrow> 0 | Cmp_Test.EQ \<Rightarrow> 1 | Cmp_Test.GT \<Rightarrow> 2]"
end
