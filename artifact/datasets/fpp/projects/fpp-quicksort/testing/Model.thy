theory Model imports Quicksort_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Quicksort_Test.linorder_class.quicksort input"
end
