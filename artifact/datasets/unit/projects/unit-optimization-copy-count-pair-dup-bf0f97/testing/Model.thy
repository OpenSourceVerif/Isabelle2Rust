theory Model imports Copy_Test begin
fun i2r_encode_2 :: "nat \<Rightarrow> nat list" where
"i2r_encode_2 x = [x]"

fun i2r_encode_1 :: "count_pair \<Rightarrow> nat list" where
"i2r_encode_1 (CountPair x0 x1) = [0] @ i2r_encode_2 (x0) @ i2r_encode_2 (x1)"

fun i2r_encode_0 :: "(count_pair \<times> count_pair) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Copy_Test.count_pair_dup ((CountPair (input ! 1) (input ! 2)) :: count_pair))"

end
