theory Model imports BorrowDemand_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BorrowDemand_Test.mtree_is_leaf ((if (input ! 0) mod 2 = 0 then (MLeaf ((input ! 1) mod 2 = 0)) else (MNode ((if (input ! 2) mod 2 = 0 then (MLeaf ((input ! 3) mod 2 = 0)) else (MNode ((MLeaf ((input ! 5) mod 2 = 0)) :: move_tree) ((MLeaf ((input ! 7) mod 2 = 0)) :: move_tree))) :: move_tree) ((if (input ! 0) mod 2 = 0 then (MLeaf ((input ! 1) mod 2 = 0)) else (MNode ((MLeaf ((input ! 3) mod 2 = 0)) :: move_tree) ((MLeaf ((input ! 5) mod 2 = 0)) :: move_tree))) :: move_tree))) :: move_tree))"

end
