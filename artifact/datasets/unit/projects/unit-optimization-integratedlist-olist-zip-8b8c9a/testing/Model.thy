theory Model imports IntegratedList_Test begin
fun i2r_encode_2 :: "nat \<Rightarrow> nat list" where
"i2r_encode_2 x = [x]"

fun i2r_encode_1 :: "(nat \<times> nat) \<Rightarrow> nat list" where
"i2r_encode_1 (x,y) = i2r_encode_2 (x) @ i2r_encode_2 (y)"

fun i2r_encode_0 :: "((nat \<times> nat) object_list) \<Rightarrow> nat list" where
"i2r_encode_0 (OEnd) = [0]"
| "i2r_encode_0 (OLink x0 x1) = [1] @ i2r_encode_1 (x0) @ i2r_encode_0 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedList_Test.olist_zip ((if (input ! 0) mod 2 = 0 then (OEnd) else (OLink (input ! 1) ((if (input ! 2) mod 2 = 0 then (OEnd) else (OLink (input ! 3) ((OEnd) :: (nat object_list)))) :: (nat object_list)))) :: (nat object_list)) ((if (input ! 5) mod 2 = 0 then (OEnd) else (OLink (input ! 6) ((if (input ! 7) mod 2 = 0 then (OEnd) else (OLink (input ! 0) ((OEnd) :: (nat object_list)))) :: (nat object_list)))) :: (nat object_list)))"

end
