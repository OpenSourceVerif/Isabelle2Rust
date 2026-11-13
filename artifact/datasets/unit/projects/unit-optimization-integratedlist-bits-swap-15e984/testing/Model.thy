theory Model imports IntegratedList_Test begin
fun i2r_encode_1 :: "bool \<Rightarrow> nat list" where
"i2r_encode_1 x = [if x then 1 else 0]"

fun i2r_encode_0 :: "bit_cell \<Rightarrow> nat list" where
"i2r_encode_0 (Bits x0 x1) = [0] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedList_Test.bits_swap ((Bits ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: bit_cell))"

end
