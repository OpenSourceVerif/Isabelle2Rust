theory Model imports CopyCalls_Test begin
fun i2r_encode_1 :: "color \<Rightarrow> nat list" where
"i2r_encode_1 (Red) = [0]"
| "i2r_encode_1 (Green) = [1]"
| "i2r_encode_1 (Blue) = [2]"

fun i2r_encode_0 :: "pixel \<Rightarrow> nat list" where
"i2r_encode_0 (Pixel x0 x1 x2) = [0] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1) @ i2r_encode_1 (x2)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.pixel_replace_first ((Pixel ((if (input ! 1) mod 3 = 0 then (Red) else (if (input ! 1) mod 3 = 1 then (Green) else (Blue))) :: color) ((if (input ! 2) mod 3 = 0 then (Red) else (if (input ! 2) mod 3 = 1 then (Green) else (Blue))) :: color) ((if (input ! 3) mod 3 = 0 then (Red) else (if (input ! 3) mod 3 = 1 then (Green) else (Blue))) :: color)) :: pixel) ((if (input ! 4) mod 3 = 0 then (Red) else (if (input ! 4) mod 3 = 1 then (Green) else (Blue))) :: color))"

end
