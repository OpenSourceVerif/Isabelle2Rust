theory Model imports IntegratedCopyBorrow_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedCopyBorrow_Test.tree_is_leaf ((if (input ! 0) mod 2 = 0 then (LLeaf ((input ! 1) mod 2 = 0)) else (LNode ((if (input ! 2) mod 2 = 0 then (LLeaf ((input ! 3) mod 2 = 0)) else (LNode ((LLeaf ((input ! 5) mod 2 = 0)) :: label_tree) ((LLeaf ((input ! 7) mod 2 = 0)) :: label_tree))) :: label_tree) ((if (input ! 0) mod 2 = 0 then (LLeaf ((input ! 1) mod 2 = 0)) else (LNode ((LLeaf ((input ! 3) mod 2 = 0)) :: label_tree) ((LLeaf ((input ! 5) mod 2 = 0)) :: label_tree))) :: label_tree))) :: label_tree))"

end
