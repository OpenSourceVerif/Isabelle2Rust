theory Model imports IntegratedNestedData_Test begin
fun i2r_encode_1 :: "bool \<Rightarrow> nat list" where
"i2r_encode_1 x = [if x then 1 else 0]"

fun i2r_encode_0 :: "leaf_tag \<Rightarrow> nat list" where
"i2r_encode_0 (Tag x0 x1 x2) = [0] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1) @ i2r_encode_1 (x2)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedNestedData_Test.tag_flip ((Tag ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: leaf_tag))"

end
