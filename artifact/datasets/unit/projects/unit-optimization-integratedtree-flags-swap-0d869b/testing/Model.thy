theory Model imports IntegratedTree_Test begin
fun i2r_encode_1 :: "bool \<Rightarrow> nat list" where
"i2r_encode_1 x = [if x then 1 else 0]"

fun i2r_encode_0 :: "flag_pair \<Rightarrow> nat list" where
"i2r_encode_0 (Flags x0 x1) = [0] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedTree_Test.flags_swap ((Flags ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: flag_pair))"

end
