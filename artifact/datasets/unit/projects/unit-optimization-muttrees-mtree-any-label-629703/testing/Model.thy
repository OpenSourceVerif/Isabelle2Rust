theory Model imports MutTrees_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (MutTrees_Test.mtree_any_label ((if (input ! 0) mod 2 = 0 then (MTLeaf ((input ! 1) mod 2 = 0)) else (MTNode ((if (input ! 2) mod 2 = 0 then (MTLeaf ((input ! 3) mod 2 = 0)) else (MTNode ((MTLeaf ((input ! 5) mod 2 = 0)) :: mut_tree) ((MTLeaf ((input ! 7) mod 2 = 0)) :: mut_tree))) :: mut_tree) ((if (input ! 0) mod 2 = 0 then (MTLeaf ((input ! 1) mod 2 = 0)) else (MTNode ((MTLeaf ((input ! 3) mod 2 = 0)) :: mut_tree) ((MTLeaf ((input ! 5) mod 2 = 0)) :: mut_tree))) :: mut_tree))) :: mut_tree))"

end
