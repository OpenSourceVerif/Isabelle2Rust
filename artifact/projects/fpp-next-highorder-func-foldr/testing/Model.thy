theory Model imports Highorder_Func_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [Highorder_Func_Test.foldr (\<lambda>x a::nat. x+2*a) input 0]"
end
