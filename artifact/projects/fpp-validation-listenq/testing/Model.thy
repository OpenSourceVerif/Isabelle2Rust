theory Model imports Queue_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Queue_Test.listenq (take (List.length input div 2) input) (drop (List.length input div 2) input)"
end
