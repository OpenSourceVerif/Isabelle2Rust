theory Model imports CopyCalls_Test begin
fun i2r_encode_1 :: "nat \<Rightarrow> nat list" where
"i2r_encode_1 x = [x]"

fun i2r_encode_0 :: "((nat, nat) copy_pair_wrap) \<Rightarrow> nat list" where
"i2r_encode_0 (CopyPairWrap x0 x1) = [0] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.pair_wrap_swap ((CopyPairWrap (input ! 1) (input ! 2)) :: ((nat, nat) copy_pair_wrap)))"

end
