theory Model imports Listprog_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [if Listprog_Test.compareTo (take (List.length input div 2) input) (drop (List.length input div 2) input) then 1 else 0]"
end
