theory Model imports Copy_Test begin
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Copy_Test.count_pair_fst ((CountPair (input ! 1) (input ! 2)) :: count_pair))"

end
