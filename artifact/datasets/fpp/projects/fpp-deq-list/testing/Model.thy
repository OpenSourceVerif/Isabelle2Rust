theory Model imports Queue_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Queue_Test.deq2list input []"
end
