theory Model imports Instances_Test begin
fun i2r_encode_1 :: "nat \<Rightarrow> nat list" where
"i2r_encode_1 x = [x]"

fun i2r_encode_0 :: "(nat wrap) \<Rightarrow> nat list" where
"i2r_encode_0 (Wrap x0) = [0] @ i2r_encode_1 (x0)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Instances_Test.inc_wrap_apply ((Wrap (input ! 1)) :: (nat wrap)))"

end
