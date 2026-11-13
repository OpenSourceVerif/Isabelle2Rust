theory Model imports BorrowDemand_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BorrowDemand_Test.ce_leaf_val ((if (input ! 0) mod 2 = 0 then (CELeaf ((input ! 1) mod 2 = 0)) else (CENode ((if (input ! 2) mod 2 = 0 then (CELeaf ((input ! 3) mod 2 = 0)) else (CENode ((CELeaf ((input ! 5) mod 2 = 0)) :: ce_tree) ((CELeaf ((input ! 7) mod 2 = 0)) :: ce_tree))) :: ce_tree) ((if (input ! 0) mod 2 = 0 then (CELeaf ((input ! 1) mod 2 = 0)) else (CENode ((CELeaf ((input ! 3) mod 2 = 0)) :: ce_tree) ((CELeaf ((input ! 5) mod 2 = 0)) :: ce_tree))) :: ce_tree))) :: ce_tree))"

end
