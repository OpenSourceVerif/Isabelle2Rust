theory Model imports Highorder_Func_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Highorder_Func_Test.map (\<lambda>x. x+1) input"
end
