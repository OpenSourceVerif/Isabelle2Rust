theory Model imports CopyCalls_Test begin
fun i2r_encode_2 :: "nat \<Rightarrow> nat list" where
"i2r_encode_2 x = [x]"

fun i2r_encode_1 :: "(nat copy_wrap) \<Rightarrow> nat list" where
"i2r_encode_1 (CopyWrap x0) = [0] @ i2r_encode_2 (x0)"

fun i2r_encode_0 :: "((nat copy_wrap) \<times> (nat copy_wrap)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.wrap_dup ((CopyWrap (input ! 1)) :: (nat copy_wrap)))"

end
