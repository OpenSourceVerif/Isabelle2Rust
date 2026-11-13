theory Model imports CopyCalls_Test begin
fun i2r_encode_0 :: "color \<Rightarrow> nat list" where
"i2r_encode_0 (Red) = [0]"
| "i2r_encode_0 (Green) = [1]"
| "i2r_encode_0 (Blue) = [2]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.pixel_first ((Pixel ((if (input ! 1) mod 3 = 0 then (Red) else (if (input ! 1) mod 3 = 1 then (Green) else (Blue))) :: color) ((if (input ! 2) mod 3 = 0 then (Red) else (if (input ! 2) mod 3 = 1 then (Green) else (Blue))) :: color) ((if (input ! 3) mod 3 = 0 then (Red) else (if (input ! 3) mod 3 = 1 then (Green) else (Blue))) :: color)) :: pixel))"

end
