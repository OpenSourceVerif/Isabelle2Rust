theory Model imports Function_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [Function_Test.add1 (input!0)]"
end
