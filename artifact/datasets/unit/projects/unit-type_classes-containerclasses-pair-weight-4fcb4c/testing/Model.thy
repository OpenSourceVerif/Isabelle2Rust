theory Model imports ContainerClasses_Test begin
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (ContainerClasses_Test.pair_weight (((input ! 1) mod 2 = 0), (if (input ! 2) mod 3 = 0 then [] else [((input ! 3) mod 2 = 0), ((input ! 4) mod 2 = 0)])))"

end
