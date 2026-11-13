theory Model imports CopyCalls_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.color_is_red ((if (input ! 0) mod 3 = 0 then (Red) else (if (input ! 0) mod 3 = 1 then (Green) else (Blue))) :: color))"

end
