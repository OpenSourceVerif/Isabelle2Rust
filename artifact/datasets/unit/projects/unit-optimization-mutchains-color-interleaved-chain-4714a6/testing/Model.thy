theory Model imports MutChains_Test begin
fun i2r_encode_0 :: "mut_color \<Rightarrow> nat list" where
"i2r_encode_0 (MRed) = [0]"
| "i2r_encode_0 (MGreen) = [1]"
| "i2r_encode_0 (MBlue) = [2]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (MutChains_Test.color_interleaved_chain ((input ! 0) mod 2 = 0) ((if (input ! 1) mod 3 = 0 then (MRed) else (if (input ! 1) mod 3 = 1 then (MGreen) else (MBlue))) :: mut_color))"

end
