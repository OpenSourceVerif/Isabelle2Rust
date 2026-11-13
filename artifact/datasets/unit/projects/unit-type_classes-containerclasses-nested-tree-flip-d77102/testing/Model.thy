theory Model imports ContainerClasses_Test begin
fun i2r_encode_2 :: "bool \<Rightarrow> nat list" where
"i2r_encode_2 x = [if x then 1 else 0]"

fun i2r_encode_1 :: "(bool class_tree) \<Rightarrow> nat list" where
"i2r_encode_1 (CTLeaf x0) = [0] @ i2r_encode_2 (x0)"
| "i2r_encode_1 (CTNode x0 x1) = [1] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

fun i2r_encode_0 :: "((bool class_tree) list) \<Rightarrow> nat list" where
"i2r_encode_0 [] = [0]"
| "i2r_encode_0 (x # xs) = 1 # (i2r_encode_1 (x) @ i2r_encode_0 xs)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (ContainerClasses_Test.nested_tree_flip (if (input ! 0) mod 3 = 0 then [] else [((if (input ! 1) mod 2 = 0 then (CTLeaf ((input ! 2) mod 2 = 0)) else (CTNode ((CTLeaf ((input ! 4) mod 2 = 0)) :: (bool class_tree)) ((CTLeaf ((input ! 6) mod 2 = 0)) :: (bool class_tree)))) :: (bool class_tree)), ((if (input ! 7) mod 2 = 0 then (CTLeaf ((input ! 0) mod 2 = 0)) else (CTNode ((CTLeaf ((input ! 2) mod 2 = 0)) :: (bool class_tree)) ((CTLeaf ((input ! 4) mod 2 = 0)) :: (bool class_tree)))) :: (bool class_tree))]))"

end
