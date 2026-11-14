theory Model imports Bubblesort_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Bubblesort_Test.linorder_class.bubblesort input"
end
