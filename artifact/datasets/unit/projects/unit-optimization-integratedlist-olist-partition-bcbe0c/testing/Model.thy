theory Model imports IntegratedList_Test begin
fun i2r_encode_3 :: "bool \<Rightarrow> nat list" where
"i2r_encode_3 x = [if x then 1 else 0]"

fun i2r_encode_2 :: "bit_cell \<Rightarrow> nat list" where
"i2r_encode_2 (Bits x0 x1) = [0] @ i2r_encode_3 (x0) @ i2r_encode_3 (x1)"

fun i2r_encode_1 :: "(bit_cell object_list) \<Rightarrow> nat list" where
"i2r_encode_1 (OEnd) = [0]"
| "i2r_encode_1 (OLink x0 x1) = [1] @ i2r_encode_2 (x0) @ i2r_encode_1 (x1)"

fun i2r_encode_0 :: "((bit_cell object_list) \<times> (bit_cell object_list)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedList_Test.olist_partition ((if (input ! 0) mod 2 = 0 then (OEnd) else (OLink ((Bits ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: bit_cell) ((if (input ! 4) mod 2 = 0 then (OEnd) else (OLink ((Bits ((input ! 6) mod 2 = 0) ((input ! 7) mod 2 = 0)) :: bit_cell) ((OEnd) :: (bit_cell object_list)))) :: (bit_cell object_list)))) :: (bit_cell object_list)))"

end
