theory Model imports IntegratedNestedData_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedNestedData_Test.tag_any ((Tag ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: leaf_tag))"

end
