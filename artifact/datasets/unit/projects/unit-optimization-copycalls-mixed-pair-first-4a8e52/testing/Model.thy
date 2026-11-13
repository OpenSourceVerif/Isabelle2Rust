theory Model imports CopyCalls_Test begin
fun i2r_encode_1 :: "bool \<Rightarrow> nat list" where
"i2r_encode_1 x = [if x then 1 else 0]"

fun i2r_encode_0 :: "flag_pair \<Rightarrow> nat list" where
"i2r_encode_0 (FlagPair x0 x1) = [0] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.mixed_pair_first ((CopyPairWrap ((FlagPair ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: flag_pair) ((if (input ! 4) mod 2 = 0 then (CopyLeaf ((input ! 5) mod 2 = 0)) else (CopyNode ((CopyLeaf ((input ! 7) mod 2 = 0)) :: copy_tree) ((CopyLeaf ((input ! 1) mod 2 = 0)) :: copy_tree))) :: copy_tree)) :: ((flag_pair, copy_tree) copy_pair_wrap)))"

end
