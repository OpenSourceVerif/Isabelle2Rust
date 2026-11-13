theory Model imports Copy_Test begin
fun i2r_encode_2 :: "bool \<Rightarrow> nat list" where
"i2r_encode_2 x = [if x then 1 else 0]"

fun i2r_encode_1 :: "small_tree \<Rightarrow> nat list" where
"i2r_encode_1 (SLeaf x0) = [0] @ i2r_encode_2 (x0)"
| "i2r_encode_1 (SNode x0 x1) = [1] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

fun i2r_encode_0 :: "(small_tree \<times> small_tree) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Copy_Test.stree_dup ((if (input ! 0) mod 2 = 0 then (SLeaf ((input ! 1) mod 2 = 0)) else (SNode ((if (input ! 2) mod 2 = 0 then (SLeaf ((input ! 3) mod 2 = 0)) else (SNode ((SLeaf ((input ! 5) mod 2 = 0)) :: small_tree) ((SLeaf ((input ! 7) mod 2 = 0)) :: small_tree))) :: small_tree) ((if (input ! 0) mod 2 = 0 then (SLeaf ((input ! 1) mod 2 = 0)) else (SNode ((SLeaf ((input ! 3) mod 2 = 0)) :: small_tree) ((SLeaf ((input ! 5) mod 2 = 0)) :: small_tree))) :: small_tree))) :: small_tree))"

end
