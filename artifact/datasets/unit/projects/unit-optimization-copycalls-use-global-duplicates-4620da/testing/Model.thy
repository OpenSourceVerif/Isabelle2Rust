theory Model imports CopyCalls_Test begin
fun i2r_encode_3 :: "bool \<Rightarrow> nat list" where
"i2r_encode_3 x = [if x then 1 else 0]"

fun i2r_encode_2 :: "global_char \<Rightarrow> nat list" where
"i2r_encode_2 (GlobalChar x0 x1) = [0] @ i2r_encode_3 (x0) @ i2r_encode_3 (x1)"

fun i2r_encode_1 :: "(global_char \<times> global_char) \<Rightarrow> nat list" where
"i2r_encode_1 (x,y) = i2r_encode_2 (x) @ i2r_encode_2 (y)"

fun i2r_encode_0 :: "((global_char \<times> global_char) \<times> (global_char \<times> global_char)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.use_global_duplicates ((GlobalChar ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: global_char))"

end
