theory Model imports Listprog_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [Listprog_Test.top input]"
end
