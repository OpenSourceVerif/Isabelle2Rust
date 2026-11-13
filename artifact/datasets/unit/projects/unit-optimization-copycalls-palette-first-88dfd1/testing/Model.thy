theory Model imports CopyCalls_Test begin
fun i2r_encode_1 :: "color \<Rightarrow> nat list" where
"i2r_encode_1 (Red) = [0]"
| "i2r_encode_1 (Green) = [1]"
| "i2r_encode_1 (Blue) = [2]"

fun i2r_encode_0 :: "pixel \<Rightarrow> nat list" where
"i2r_encode_0 (Pixel x0 x1 x2) = [0] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1) @ i2r_encode_1 (x2)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.palette_first ((Palette ((Pixel ((Red) :: color) ((Red) :: color) ((Red) :: color)) :: pixel) ((Pixel ((Red) :: color) ((Red) :: color) ((Red) :: color)) :: pixel)) :: palette))"

end
