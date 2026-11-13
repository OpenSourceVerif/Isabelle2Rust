theory Model imports IntegratedList_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedList_Test.olist_all ((if (input ! 0) mod 2 = 0 then (OEnd) else (OLink ((Bits ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: bit_cell) ((if (input ! 4) mod 2 = 0 then (OEnd) else (OLink ((Bits ((input ! 6) mod 2 = 0) ((input ! 7) mod 2 = 0)) :: bit_cell) ((OEnd) :: (bit_cell object_list)))) :: (bit_cell object_list)))) :: (bit_cell object_list)))"

end
