theory Model imports MutTrees_Test begin
fun i2r_encode_1 :: "bool \<Rightarrow> nat list" where
"i2r_encode_1 x = [if x then 1 else 0]"

fun i2r_encode_0 :: "mut_tree \<Rightarrow> nat list" where
"i2r_encode_0 (MTLeaf x0) = [0] @ i2r_encode_1 (x0)"
| "i2r_encode_0 (MTNode x0 x1) = [1] @ i2r_encode_0 (x0) @ i2r_encode_0 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (MutTrees_Test.mtree_interleaved_chain ((input ! 0) mod 2 = 0) ((if (input ! 1) mod 2 = 0 then (MTLeaf ((input ! 2) mod 2 = 0)) else (MTNode ((if (input ! 3) mod 2 = 0 then (MTLeaf ((input ! 4) mod 2 = 0)) else (MTNode ((MTLeaf ((input ! 6) mod 2 = 0)) :: mut_tree) ((MTLeaf ((input ! 0) mod 2 = 0)) :: mut_tree))) :: mut_tree) ((if (input ! 1) mod 2 = 0 then (MTLeaf ((input ! 2) mod 2 = 0)) else (MTNode ((MTLeaf ((input ! 4) mod 2 = 0)) :: mut_tree) ((MTLeaf ((input ! 6) mod 2 = 0)) :: mut_tree))) :: mut_tree))) :: mut_tree))"

end
