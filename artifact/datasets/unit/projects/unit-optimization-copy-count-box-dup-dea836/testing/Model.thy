theory Model imports Copy_Test begin
fun i2r_encode_2 :: "nat \<Rightarrow> nat list" where
"i2r_encode_2 x = [x]"

fun i2r_encode_1 :: "count_box \<Rightarrow> nat list" where
"i2r_encode_1 (CountBox x0) = [0] @ i2r_encode_2 (x0)"

fun i2r_encode_0 :: "(count_box \<times> count_box) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Copy_Test.count_box_dup ((CountBox (input ! 1)) :: count_box))"

end
