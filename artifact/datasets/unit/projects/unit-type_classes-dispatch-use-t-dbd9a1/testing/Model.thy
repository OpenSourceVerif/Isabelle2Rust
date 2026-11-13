theory Model imports Dispatch_Test begin
fun i2r_encode_0 :: "T \<Rightarrow> nat list" where
"i2r_encode_0 (A) = [0]"
| "i2r_encode_0 (B) = [1]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Dispatch_Test.use_t)"

end
