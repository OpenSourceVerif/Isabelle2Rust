theory Model imports IntegratedList_Test begin
fun i2r_encode_1 :: "nat \<Rightarrow> nat list" where
"i2r_encode_1 x = [x]"

fun i2r_encode_0 :: "(nat object_list) \<Rightarrow> nat list" where
"i2r_encode_0 (OEnd) = [0]"
| "i2r_encode_0 (OLink x0 x1) = [1] @ i2r_encode_1 (x0) @ i2r_encode_0 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedList_Test.olist_append ((if (input ! 0) mod 2 = 0 then (OEnd) else (OLink (input ! 1) ((if (input ! 2) mod 2 = 0 then (OEnd) else (OLink (input ! 3) ((OEnd) :: (nat object_list)))) :: (nat object_list)))) :: (nat object_list)) ((if (input ! 5) mod 2 = 0 then (OEnd) else (OLink (input ! 6) ((if (input ! 7) mod 2 = 0 then (OEnd) else (OLink (input ! 0) ((OEnd) :: (nat object_list)))) :: (nat object_list)))) :: (nat object_list)))"

end
