theory Model imports CopyCalls_Test begin
fun i2r_encode_2 :: "color \<Rightarrow> nat list" where
"i2r_encode_2 (Red) = [0]"
| "i2r_encode_2 (Green) = [1]"
| "i2r_encode_2 (Blue) = [2]"

fun i2r_encode_1 :: "pixel \<Rightarrow> nat list" where
"i2r_encode_1 (Pixel x0 x1 x2) = [0] @ i2r_encode_2 (x0) @ i2r_encode_2 (x1) @ i2r_encode_2 (x2)"

fun i2r_encode_0 :: "palette \<Rightarrow> nat list" where
"i2r_encode_0 (Palette x0 x1) = [0] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.palette_swap ((Palette ((Pixel ((Red) :: color) ((Red) :: color) ((Red) :: color)) :: pixel) ((Pixel ((Red) :: color) ((Red) :: color) ((Red) :: color)) :: pixel)) :: palette))"

end
