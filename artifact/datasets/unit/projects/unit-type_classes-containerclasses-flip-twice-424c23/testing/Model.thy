theory Model imports ContainerClasses_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (ContainerClasses_Test.flip_twice ((input ! 0) mod 2 = 0))"

end
