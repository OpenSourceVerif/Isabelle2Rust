theory Model imports IntegratedList_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedList_Test.olist_is_empty ((if (input ! 0) mod 2 = 0 then (OEnd) else (OLink (input ! 1) ((if (input ! 2) mod 2 = 0 then (OEnd) else (OLink (input ! 3) ((OEnd) :: (nat object_list)))) :: (nat object_list)))) :: (nat object_list)))"

end
