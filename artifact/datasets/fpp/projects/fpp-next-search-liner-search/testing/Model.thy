theory Model imports search_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (case search_Test.liner_search (hd(input@[0])) (tl input) of None \<Rightarrow> [0] | Some n \<Rightarrow> [1,n])"
end
