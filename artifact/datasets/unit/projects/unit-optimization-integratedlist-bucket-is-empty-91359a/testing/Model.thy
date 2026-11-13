theory Model imports IntegratedList_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedList_Test.bucket_is_empty ((BitBucket ((if (input ! 1) mod 2 = 0 then (OEnd) else (OLink ((Bits ((input ! 3) mod 2 = 0) ((input ! 4) mod 2 = 0)) :: bit_cell) ((OEnd) :: (bit_cell object_list)))) :: (bit_cell object_list)) ((input ! 6) mod 2 = 0)) :: bit_bucket))"

end
