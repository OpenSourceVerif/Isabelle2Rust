theory Model imports BuiltinInstances_Test begin
fun i2r_encode_0 :: "int \<Rightarrow> nat list" where
"i2r_encode_0 x = [nat x, nat (-x)]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BuiltinInstances_Test.pick_int ((input ! 0) mod 2 = 0))"

end
