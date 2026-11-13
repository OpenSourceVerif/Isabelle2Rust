theory Model imports CopyCalls_Test begin
fun i2r_encode_2 :: "bool \<Rightarrow> nat list" where
"i2r_encode_2 x = [if x then 1 else 0]"

fun i2r_encode_1 :: "copy_tree \<Rightarrow> nat list" where
"i2r_encode_1 (CopyLeaf x0) = [0] @ i2r_encode_2 (x0)"
| "i2r_encode_1 (CopyNode x0 x1) = [1] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

fun i2r_encode_0 :: "(copy_tree \<times> copy_tree) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.tree_dup ((if (input ! 0) mod 2 = 0 then (CopyLeaf ((input ! 1) mod 2 = 0)) else (CopyNode ((if (input ! 2) mod 2 = 0 then (CopyLeaf ((input ! 3) mod 2 = 0)) else (CopyNode ((CopyLeaf ((input ! 5) mod 2 = 0)) :: copy_tree) ((CopyLeaf ((input ! 7) mod 2 = 0)) :: copy_tree))) :: copy_tree) ((if (input ! 0) mod 2 = 0 then (CopyLeaf ((input ! 1) mod 2 = 0)) else (CopyNode ((CopyLeaf ((input ! 3) mod 2 = 0)) :: copy_tree) ((CopyLeaf ((input ! 5) mod 2 = 0)) :: copy_tree))) :: copy_tree))) :: copy_tree))"

end
