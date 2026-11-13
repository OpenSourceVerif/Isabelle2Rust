theory Model imports BuiltinInstances_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BuiltinInstances_Test.eq_pair ((input ! 1), (input ! 2)))"

end
