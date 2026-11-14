theory Model imports Highorder_Func_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [Highorder_Func_Test.fof2 (input!0,input!1)]"
end
