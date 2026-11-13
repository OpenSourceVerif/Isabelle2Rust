theory Model imports BorrowDemand_Test begin
fun i2r_encode_1 :: "bool \<Rightarrow> nat list" where
"i2r_encode_1 x = [if x then 1 else 0]"

fun i2r_encode_0 :: "move_tree \<Rightarrow> nat list" where
"i2r_encode_0 (MLeaf x0) = [0] @ i2r_encode_1 (x0)"
| "i2r_encode_0 (MNode x0 x1) = [1] @ i2r_encode_0 (x0) @ i2r_encode_0 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BorrowDemand_Test.mtree_identity ((if (input ! 0) mod 2 = 0 then (MLeaf ((input ! 1) mod 2 = 0)) else (MNode ((if (input ! 2) mod 2 = 0 then (MLeaf ((input ! 3) mod 2 = 0)) else (MNode ((MLeaf ((input ! 5) mod 2 = 0)) :: move_tree) ((MLeaf ((input ! 7) mod 2 = 0)) :: move_tree))) :: move_tree) ((if (input ! 0) mod 2 = 0 then (MLeaf ((input ! 1) mod 2 = 0)) else (MNode ((MLeaf ((input ! 3) mod 2 = 0)) :: move_tree) ((MLeaf ((input ! 5) mod 2 = 0)) :: move_tree))) :: move_tree))) :: move_tree))"

end
