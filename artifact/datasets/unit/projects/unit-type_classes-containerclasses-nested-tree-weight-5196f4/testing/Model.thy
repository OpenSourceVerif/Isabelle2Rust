theory Model imports ContainerClasses_Test begin
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (ContainerClasses_Test.nested_tree_weight (if (input ! 0) mod 3 = 0 then [] else [((if (input ! 1) mod 2 = 0 then (CTLeaf ((input ! 2) mod 2 = 0)) else (CTNode ((CTLeaf ((input ! 4) mod 2 = 0)) :: (bool class_tree)) ((CTLeaf ((input ! 6) mod 2 = 0)) :: (bool class_tree)))) :: (bool class_tree)), ((if (input ! 7) mod 2 = 0 then (CTLeaf ((input ! 0) mod 2 = 0)) else (CTNode ((CTLeaf ((input ! 2) mod 2 = 0)) :: (bool class_tree)) ((CTLeaf ((input ! 4) mod 2 = 0)) :: (bool class_tree)))) :: (bool class_tree))]))"

end
