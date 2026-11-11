theory Model imports "source/4_ds_algo/bintree/AVL_Set_Code_Test" begin
fun encode_352bcd74a0 :: "((nat \<times> nat) Tree_Test.tree) \<Rightarrow> nat list" where
 "encode_352bcd74a0 (Tree_Test.tree.Leaf ) = (List.Cons 0 List.Nil)" |
 "encode_352bcd74a0 (Tree_Test.tree.Node v0 v1 v2) = (List.Cons 1 (List.append (encode_352bcd74a0 (v0)) (List.append (List.append (List.Cons ((fst (v1))) List.Nil) (List.Cons ((snd (v1))) List.Nil)) (List.append (encode_352bcd74a0 (v2)) List.Nil))))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((AVL_Set_Code_Test.empty :: ((nat \<times> nat) Tree_Test.tree)) ) in (encode_352bcd74a0 (result)))"
end
