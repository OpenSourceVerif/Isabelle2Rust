theory Model imports Function_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (case Function_Test.Pred (input!0) of None \<Rightarrow> [0] | Some n \<Rightarrow> [1,n])"
end
