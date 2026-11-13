theory Model imports ContainerClasses_Test begin
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (ContainerClasses_Test.generic_weight ((input ! 0) mod 2 = 0))"

end
