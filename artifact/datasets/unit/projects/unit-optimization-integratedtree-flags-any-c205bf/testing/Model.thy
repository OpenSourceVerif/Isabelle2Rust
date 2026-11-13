theory Model imports IntegratedTree_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedTree_Test.flags_any ((Flags ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: flag_pair))"

end
