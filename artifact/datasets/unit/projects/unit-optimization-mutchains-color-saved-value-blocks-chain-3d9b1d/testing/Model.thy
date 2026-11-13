theory Model imports MutChains_Test begin
fun i2r_encode_1 :: "mut_color \<Rightarrow> nat list" where
"i2r_encode_1 (MRed) = [0]"
| "i2r_encode_1 (MGreen) = [1]"
| "i2r_encode_1 (MBlue) = [2]"

fun i2r_encode_0 :: "(mut_color \<times> mut_color) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (MutChains_Test.color_saved_value_blocks_chain ((if (input ! 0) mod 3 = 0 then (MRed) else (if (input ! 0) mod 3 = 1 then (MGreen) else (MBlue))) :: mut_color))"

end
