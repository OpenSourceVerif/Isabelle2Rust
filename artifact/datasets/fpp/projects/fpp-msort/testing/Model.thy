theory Model imports MergeSort_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = MergeSort_Test.linorder_class.msort input"
end
