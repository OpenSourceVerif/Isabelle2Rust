theory Model imports CopyCalls_Test begin
fun i2r_encode_1 :: "color \<Rightarrow> nat list" where
"i2r_encode_1 (Red) = [0]"
| "i2r_encode_1 (Green) = [1]"
| "i2r_encode_1 (Blue) = [2]"

fun i2r_encode_0 :: "(color \<times> color) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.color_dup ((if (input ! 0) mod 3 = 0 then (Red) else (if (input ! 0) mod 3 = 1 then (Green) else (Blue))) :: color))"

end
