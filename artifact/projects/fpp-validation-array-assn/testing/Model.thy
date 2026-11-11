theory Model imports Function_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Function_Test.array_assn (tl input) (hd (input@[0]) mod Suc (Suc (List.length (tl input)))) (List.length input)"
end
