theory Model imports BuiltinInstances_Test begin
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BuiltinInstances_Test.set_color (\<lambda>_. (input ! 1)) ((if (input ! 2) mod 3 = 0 then (Red) else (if (input ! 2) mod 3 = 1 then (Green) else (Blue))) :: color) (input ! 3) ((if (input ! 4) mod 3 = 0 then (Red) else (if (input ! 4) mod 3 = 1 then (Green) else (Blue))) :: color))"

end
