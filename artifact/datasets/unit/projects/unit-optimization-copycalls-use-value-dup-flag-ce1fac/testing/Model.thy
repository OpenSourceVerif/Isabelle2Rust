theory Model imports CopyCalls_Test begin
fun i2r_encode_2 :: "bool \<Rightarrow> nat list" where
"i2r_encode_2 x = [if x then 1 else 0]"

fun i2r_encode_1 :: "flag_pair \<Rightarrow> nat list" where
"i2r_encode_1 (FlagPair x0 x1) = [0] @ i2r_encode_2 (x0) @ i2r_encode_2 (x1)"

fun i2r_encode_0 :: "(flag_pair \<times> flag_pair) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.use_value_dup_flag ((FlagPair ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: flag_pair))"

end
