theory Model imports MergeSort_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = MergeSort_Test.linorder_class.merge (sort (take (length input div 2) input)) (sort (drop (length input div 2) input))"
end
