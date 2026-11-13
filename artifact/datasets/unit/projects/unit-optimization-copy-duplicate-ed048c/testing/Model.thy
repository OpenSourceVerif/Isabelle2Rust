theory Model imports Copy_Test begin
fun i2r_encode_1 :: "nat \<Rightarrow> nat list" where
"i2r_encode_1 x = [x]"

fun i2r_encode_0 :: "(nat \<times> nat) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Copy_Test.duplicate (input ! 0))"

end
