theory Model imports CopyCalls_Test begin
fun i2r_encode_2 :: "nat \<Rightarrow> nat list" where
"i2r_encode_2 x = [x]"

fun i2r_encode_1 :: "((nat, nat) copy_pair_wrap) \<Rightarrow> nat list" where
"i2r_encode_1 (CopyPairWrap x0 x1) = [0] @ i2r_encode_2 (x0) @ i2r_encode_2 (x1)"

fun i2r_encode_0 :: "(((nat, nat) copy_pair_wrap) \<times> ((nat, nat) copy_pair_wrap)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.pair_wrap_dup ((CopyPairWrap (input ! 1) (input ! 2)) :: ((nat, nat) copy_pair_wrap)))"

end
