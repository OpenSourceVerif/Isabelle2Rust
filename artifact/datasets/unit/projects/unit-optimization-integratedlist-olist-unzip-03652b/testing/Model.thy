theory Model imports IntegratedList_Test begin
fun i2r_encode_2 :: "nat \<Rightarrow> nat list" where
"i2r_encode_2 x = [x]"

fun i2r_encode_1 :: "(nat object_list) \<Rightarrow> nat list" where
"i2r_encode_1 (OEnd) = [0]"
| "i2r_encode_1 (OLink x0 x1) = [1] @ i2r_encode_2 (x0) @ i2r_encode_1 (x1)"

fun i2r_encode_0 :: "((nat object_list) \<times> (nat object_list)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedList_Test.olist_unzip ((if (input ! 0) mod 2 = 0 then (OEnd) else (OLink ((input ! 2), (input ! 3)) ((if (input ! 4) mod 2 = 0 then (OEnd) else (OLink ((input ! 6), (input ! 7)) ((OEnd) :: ((nat \<times> nat) object_list)))) :: ((nat \<times> nat) object_list)))) :: ((nat \<times> nat) object_list)))"

end
