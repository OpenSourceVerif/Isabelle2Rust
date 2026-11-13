theory Model imports IntegratedCopyBorrow_Test begin
fun i2r_encode_2 :: "bool \<Rightarrow> nat list" where
"i2r_encode_2 x = [if x then 1 else 0]"

fun i2r_encode_1 :: "label_tree \<Rightarrow> nat list" where
"i2r_encode_1 (LLeaf x0) = [0] @ i2r_encode_2 (x0)"
| "i2r_encode_1 (LNode x0 x1) = [1] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

fun i2r_encode_0 :: "(label_tree \<times> label_tree) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedCopyBorrow_Test.tree_dup ((if (input ! 0) mod 2 = 0 then (LLeaf ((input ! 1) mod 2 = 0)) else (LNode ((if (input ! 2) mod 2 = 0 then (LLeaf ((input ! 3) mod 2 = 0)) else (LNode ((LLeaf ((input ! 5) mod 2 = 0)) :: label_tree) ((LLeaf ((input ! 7) mod 2 = 0)) :: label_tree))) :: label_tree) ((if (input ! 0) mod 2 = 0 then (LLeaf ((input ! 1) mod 2 = 0)) else (LNode ((LLeaf ((input ! 3) mod 2 = 0)) :: label_tree) ((LLeaf ((input ! 5) mod 2 = 0)) :: label_tree))) :: label_tree))) :: label_tree))"

end
