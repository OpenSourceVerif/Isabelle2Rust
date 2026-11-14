theory Model imports "source/2_functionalprog/Types_Test" begin
fun encode_5c7c389322 :: "((char list) Types_Test.Tree) \<Rightarrow> nat list" where
 "encode_5c7c389322 (Types_Test.Tree.Leaf i2r_observation_field_b86ad274f4_0) = (List.Cons 0 (List.append (List.Cons (List.length (i2r_observation_field_b86ad274f4_0)) (List.concat (List.map (\<lambda>v. (List.Cons ((of_char (v) :: nat)) List.Nil)) (i2r_observation_field_b86ad274f4_0)))) List.Nil))" |
 "encode_5c7c389322 (Types_Test.Tree.Node i2r_observation_field_b86ad274f4_0 i2r_observation_field_b86ad274f4_1 i2r_observation_field_b86ad274f4_2) = (List.Cons 1 (List.append (encode_5c7c389322 (i2r_observation_field_b86ad274f4_0)) (List.append (List.Cons (List.length (i2r_observation_field_b86ad274f4_1)) (List.concat (List.map (\<lambda>v. (List.Cons ((of_char (v) :: nat)) List.Nil)) (i2r_observation_field_b86ad274f4_1)))) (List.append (encode_5c7c389322 (i2r_observation_field_b86ad274f4_2)) List.Nil))))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Types_Test.Tree2 :: ((char list) Types_Test.Tree)) ) in (encode_5c7c389322 (result)))"
end
