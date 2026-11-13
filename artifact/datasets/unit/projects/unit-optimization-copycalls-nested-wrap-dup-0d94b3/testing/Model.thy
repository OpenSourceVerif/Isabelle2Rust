theory Model imports CopyCalls_Test begin
fun i2r_encode_3 :: "nat \<Rightarrow> nat list" where
"i2r_encode_3 x = [x]"

fun i2r_encode_2 :: "(nat copy_wrap) \<Rightarrow> nat list" where
"i2r_encode_2 (CopyWrap x0) = [0] @ i2r_encode_3 (x0)"

fun i2r_encode_1 :: "(nat nested_copy_wrap) \<Rightarrow> nat list" where
"i2r_encode_1 (NestedCopyWrap x0) = [0] @ i2r_encode_2 (x0)"

fun i2r_encode_0 :: "((nat nested_copy_wrap) \<times> (nat nested_copy_wrap)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.nested_wrap_dup ((NestedCopyWrap ((CopyWrap (input ! 2)) :: (nat copy_wrap))) :: (nat nested_copy_wrap)))"

end
