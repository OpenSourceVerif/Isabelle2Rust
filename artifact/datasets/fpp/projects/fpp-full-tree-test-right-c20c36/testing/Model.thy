theory Model imports "source/4_ds_algo/bintree/Tree_Test" begin
definition fixture_fcc391b11b_0 :: "nat \<Rightarrow> (nat Tree_Test.tree)" where
 "fixture_fcc391b11b_0 s = (Tree_Test.tree.Leaf )"

definition fixture_fcc391b11b_1 :: "nat \<Rightarrow> (nat Tree_Test.tree)" where
 "fixture_fcc391b11b_1 s = (if s mod 2 = 0 then (Tree_Test.tree.Leaf ) else (Tree_Test.tree.Node ((fixture_fcc391b11b_0 (s + 1))) (((s + 2) mod 9)) ((fixture_fcc391b11b_0 (s + 3)))))"

definition fixture_fcc391b11b_2 :: "nat \<Rightarrow> (nat Tree_Test.tree)" where
 "fixture_fcc391b11b_2 s = (if s mod 2 = 0 then (Tree_Test.tree.Leaf ) else (Tree_Test.tree.Node ((fixture_fcc391b11b_1 (s + 1))) (((s + 2) mod 9)) ((fixture_fcc391b11b_1 (s + 3)))))"

fun encode_fcc391b11b :: "(nat Tree_Test.tree) \<Rightarrow> nat list" where
 "encode_fcc391b11b (Tree_Test.tree.Leaf ) = (List.Cons 0 List.Nil)" |
 "encode_fcc391b11b (Tree_Test.tree.Node v0 v1 v2) = (List.Cons 1 (List.append (encode_fcc391b11b (v0)) (List.append (List.Cons (v1) List.Nil) (List.append (encode_fcc391b11b (v2)) List.Nil))))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Tree_Test.right :: ((nat Tree_Test.tree) \<Rightarrow> (nat Tree_Test.tree))) ((fixture_fcc391b11b_2 ((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0))))) in (encode_fcc391b11b (result)))"
end
