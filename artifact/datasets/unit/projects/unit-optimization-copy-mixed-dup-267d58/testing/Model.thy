theory Model imports Copy_Test begin
fun i2r_encode_2 :: "bool \<Rightarrow> nat list" where
"i2r_encode_2 x = [if x then 1 else 0]"

fun i2r_encode_3 :: "nat \<Rightarrow> nat list" where
"i2r_encode_3 x = [x]"

fun i2r_encode_1 :: "mixed_count \<Rightarrow> nat list" where
"i2r_encode_1 (MixedCount x0 x1) = [0] @ i2r_encode_2 (x0) @ i2r_encode_3 (x1)"

fun i2r_encode_0 :: "(mixed_count \<times> mixed_count) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Copy_Test.mixed_dup ((MixedCount ((input ! 1) mod 2 = 0) (input ! 2)) :: mixed_count))"

end
