theory Model imports Copy_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Copy_Test.stree_is_leaf ((if (input ! 0) mod 2 = 0 then (SLeaf ((input ! 1) mod 2 = 0)) else (SNode ((if (input ! 2) mod 2 = 0 then (SLeaf ((input ! 3) mod 2 = 0)) else (SNode ((SLeaf ((input ! 5) mod 2 = 0)) :: small_tree) ((SLeaf ((input ! 7) mod 2 = 0)) :: small_tree))) :: small_tree) ((if (input ! 0) mod 2 = 0 then (SLeaf ((input ! 1) mod 2 = 0)) else (SNode ((SLeaf ((input ! 3) mod 2 = 0)) :: small_tree) ((SLeaf ((input ! 5) mod 2 = 0)) :: small_tree))) :: small_tree))) :: small_tree))"

end
