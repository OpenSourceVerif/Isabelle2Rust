theory Model imports CopyCalls_Test begin
fun i2r_encode_1 :: "bool \<Rightarrow> nat list" where
"i2r_encode_1 x = [if x then 1 else 0]"

fun i2r_encode_0 :: "flag_triple \<Rightarrow> nat list" where
"i2r_encode_0 (FlagTriple x0 x1 x2) = [0] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1) @ i2r_encode_1 (x2)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.triple_rotate ((FlagTriple ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: flag_triple))"

end
