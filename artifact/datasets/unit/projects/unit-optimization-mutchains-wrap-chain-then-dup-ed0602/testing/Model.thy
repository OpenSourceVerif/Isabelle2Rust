theory Model imports MutChains_Test begin
fun i2r_encode_2 :: "nat \<Rightarrow> nat list" where
"i2r_encode_2 x = [x]"

fun i2r_encode_1 :: "(nat mut_wrap) \<Rightarrow> nat list" where
"i2r_encode_1 (MutWrap x0) = [0] @ i2r_encode_2 (x0)"

fun i2r_encode_0 :: "((nat mut_wrap) \<times> (nat mut_wrap)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (MutChains_Test.wrap_chain_then_dup ((MutWrap (input ! 1)) :: (nat mut_wrap)))"

end
