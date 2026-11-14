theory Model imports Highorder_Func_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [Highorder_Func_Test.hof2 (hd (input@[0])) (\<lambda>x y. x+2*y) (length input)]"
end
