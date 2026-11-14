theory Model imports Highorder_Func_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Highorder_Func_Test.filter (\<lambda>x::nat. x mod 2=0) input"
end
