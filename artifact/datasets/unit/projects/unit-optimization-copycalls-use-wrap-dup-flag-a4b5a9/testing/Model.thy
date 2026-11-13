theory Model imports CopyCalls_Test begin
fun i2r_encode_3 :: "bool \<Rightarrow> nat list" where
"i2r_encode_3 x = [if x then 1 else 0]"

fun i2r_encode_2 :: "flag_pair \<Rightarrow> nat list" where
"i2r_encode_2 (FlagPair x0 x1) = [0] @ i2r_encode_3 (x0) @ i2r_encode_3 (x1)"

fun i2r_encode_1 :: "(flag_pair copy_wrap) \<Rightarrow> nat list" where
"i2r_encode_1 (CopyWrap x0) = [0] @ i2r_encode_2 (x0)"

fun i2r_encode_0 :: "((flag_pair copy_wrap) \<times> (flag_pair copy_wrap)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.use_wrap_dup_flag ((CopyWrap ((FlagPair ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: flag_pair)) :: (flag_pair copy_wrap)))"

end
