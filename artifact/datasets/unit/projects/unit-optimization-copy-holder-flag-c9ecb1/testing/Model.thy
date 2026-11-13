theory Model imports Copy_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Copy_Test.holder_flag ((TreeHolder ((if (input ! 1) mod 2 = 0 then (SLeaf ((input ! 2) mod 2 = 0)) else (SNode ((SLeaf ((input ! 4) mod 2 = 0)) :: small_tree) ((SLeaf ((input ! 6) mod 2 = 0)) :: small_tree))) :: small_tree) ((input ! 7) mod 2 = 0)) :: tree_holder))"

end
