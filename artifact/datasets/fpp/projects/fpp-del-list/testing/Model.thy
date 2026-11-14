theory Model imports List_Ins_Del_Test begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = List_Ins_Del_Test.del_list (length input mod 8) input"
end
