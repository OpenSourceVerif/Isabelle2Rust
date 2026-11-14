theory Model imports Highorder_Func_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [Highorder_Func_Test.foldl (\<lambda>a x::nat. 2*a+x) 0 input]"
end
