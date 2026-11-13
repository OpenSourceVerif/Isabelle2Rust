theory Model imports CopyCalls_Test begin
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.wrap_unwrap ((CopyWrap (input ! 1)) :: (nat copy_wrap)))"

end
