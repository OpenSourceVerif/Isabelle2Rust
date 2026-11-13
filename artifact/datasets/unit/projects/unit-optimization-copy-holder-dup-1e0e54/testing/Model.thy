theory Model imports Copy_Test begin
fun i2r_encode_3 :: "bool \<Rightarrow> nat list" where
"i2r_encode_3 x = [if x then 1 else 0]"

fun i2r_encode_2 :: "small_tree \<Rightarrow> nat list" where
"i2r_encode_2 (SLeaf x0) = [0] @ i2r_encode_3 (x0)"
| "i2r_encode_2 (SNode x0 x1) = [1] @ i2r_encode_2 (x0) @ i2r_encode_2 (x1)"

fun i2r_encode_1 :: "tree_holder \<Rightarrow> nat list" where
"i2r_encode_1 (TreeHolder x0 x1) = [0] @ i2r_encode_2 (x0) @ i2r_encode_3 (x1)"

fun i2r_encode_0 :: "(tree_holder \<times> tree_holder) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Copy_Test.holder_dup ((TreeHolder ((if (input ! 1) mod 2 = 0 then (SLeaf ((input ! 2) mod 2 = 0)) else (SNode ((SLeaf ((input ! 4) mod 2 = 0)) :: small_tree) ((SLeaf ((input ! 6) mod 2 = 0)) :: small_tree))) :: small_tree) ((input ! 7) mod 2 = 0)) :: tree_holder))"

end
