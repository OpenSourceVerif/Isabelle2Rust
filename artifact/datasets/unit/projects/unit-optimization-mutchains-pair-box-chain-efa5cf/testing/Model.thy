theory Model imports MutChains_Test begin
fun i2r_encode_1 :: "nat \<Rightarrow> nat list" where
"i2r_encode_1 x = [x]"

fun i2r_encode_0 :: "(nat mut_pair_box) \<Rightarrow> nat list" where
"i2r_encode_0 (MutPairBox x0 x1) = [0] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (MutChains_Test.pair_box_chain ((MutPairBox (input ! 1) (input ! 2)) :: (nat mut_pair_box)))"

end
