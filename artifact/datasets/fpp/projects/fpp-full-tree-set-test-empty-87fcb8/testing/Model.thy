theory Model imports "source/4_ds_algo/bintree/Tree_Set_Test" begin
fun encode_fcc391b11b :: "(nat Tree_Test.tree) \<Rightarrow> nat list" where
 "encode_fcc391b11b (Tree_Test.tree.Leaf ) = (List.Cons 0 List.Nil)" |
 "encode_fcc391b11b (Tree_Test.tree.Node v0 v1 v2) = (List.Cons 1 (List.append (encode_fcc391b11b (v0)) (List.append (List.Cons (v1) List.Nil) (List.append (encode_fcc391b11b (v2)) List.Nil))))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Tree_Set_Test.empty :: (nat Tree_Test.tree)) ) in (encode_fcc391b11b (result)))"
end
