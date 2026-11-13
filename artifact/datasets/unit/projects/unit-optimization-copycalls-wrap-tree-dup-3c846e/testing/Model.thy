theory Model imports CopyCalls_Test begin
fun i2r_encode_3 :: "bool \<Rightarrow> nat list" where
"i2r_encode_3 x = [if x then 1 else 0]"

fun i2r_encode_2 :: "copy_tree \<Rightarrow> nat list" where
"i2r_encode_2 (CopyLeaf x0) = [0] @ i2r_encode_3 (x0)"
| "i2r_encode_2 (CopyNode x0 x1) = [1] @ i2r_encode_2 (x0) @ i2r_encode_2 (x1)"

fun i2r_encode_1 :: "(copy_tree copy_wrap) \<Rightarrow> nat list" where
"i2r_encode_1 (CopyWrap x0) = [0] @ i2r_encode_2 (x0)"

fun i2r_encode_0 :: "((copy_tree copy_wrap) \<times> (copy_tree copy_wrap)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.wrap_tree_dup ((CopyWrap ((if (input ! 1) mod 2 = 0 then (CopyLeaf ((input ! 2) mod 2 = 0)) else (CopyNode ((CopyLeaf ((input ! 4) mod 2 = 0)) :: copy_tree) ((CopyLeaf ((input ! 6) mod 2 = 0)) :: copy_tree))) :: copy_tree)) :: (copy_tree copy_wrap)))"

end
