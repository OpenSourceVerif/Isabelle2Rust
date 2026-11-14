theory Model imports Tutorial_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Tutorial_Test.rev_append (take (List.length input div 2) input) (drop (List.length input div 2) input)"
end
