theory Model imports "source/4_ds_algo/bintree/AVL_Set_Code_Test" begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((AVL_Set_Code_Test.ht :: (((nat \<times> nat) Tree_Test.tree) \<Rightarrow> nat)) ((if ((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0)) mod 2 = 0 then Tree_Test.Leaf else Tree_Test.Node Tree_Test.Leaf (Product_Type.Pair (((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0)) mod 9) 1) Tree_Test.Leaf))) in (List.Cons (result) List.Nil))"
end
