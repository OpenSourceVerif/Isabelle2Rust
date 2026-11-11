theory Model imports Listprog_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (if input=[] then [] else [Listprog_Test.charAt input (length input div 2)])"
end
