theory Model imports stack_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [if stack_Test.emp input then 1 else 0]"
end
