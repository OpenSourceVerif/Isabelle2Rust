theory Model imports InsertSort_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = InsertSort_Test.linorder_class.insort (length input) (sort input)"
end
