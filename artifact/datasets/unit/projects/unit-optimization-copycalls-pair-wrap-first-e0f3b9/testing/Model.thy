theory Model imports CopyCalls_Test begin
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.pair_wrap_first ((CopyPairWrap (input ! 1) (input ! 2)) :: ((nat, nat) copy_pair_wrap)))"

end
