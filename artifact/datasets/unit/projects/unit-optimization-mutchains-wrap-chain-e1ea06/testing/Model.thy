theory Model imports MutChains_Test begin
fun i2r_encode_1 :: "nat \<Rightarrow> nat list" where
"i2r_encode_1 x = [x]"

fun i2r_encode_0 :: "(nat mut_wrap) \<Rightarrow> nat list" where
"i2r_encode_0 (MutWrap x0) = [0] @ i2r_encode_1 (x0)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (MutChains_Test.wrap_chain ((MutWrap (input ! 1)) :: (nat mut_wrap)))"

end
