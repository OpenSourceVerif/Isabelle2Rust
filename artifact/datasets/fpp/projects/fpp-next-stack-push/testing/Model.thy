theory Model imports stack_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = stack_Test.push (List.length input) input"
end
