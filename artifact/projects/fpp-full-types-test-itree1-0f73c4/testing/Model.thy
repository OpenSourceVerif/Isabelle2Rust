theory Model imports "source/2_functionalprog/Types_Test" begin
fun encode_f01d95ec74 :: "Types_Test.ITree \<Rightarrow> nat list" where
 "encode_f01d95ec74 (Types_Test.ITree.Leaf i2r_observation_field_0e19c39778_0) = (List.Cons 0 (List.append (List.Cons (if (i2r_observation_field_0e19c39778_0) < 0 then nat (-2*(i2r_observation_field_0e19c39778_0)-1) else nat (2*(i2r_observation_field_0e19c39778_0))) List.Nil) List.Nil))" |
 "encode_f01d95ec74 (Types_Test.ITree.Node i2r_observation_field_0e19c39778_0 i2r_observation_field_0e19c39778_1 i2r_observation_field_0e19c39778_2) = (List.Cons 1 (List.append (encode_f01d95ec74 (i2r_observation_field_0e19c39778_0)) (List.append (List.Cons (if (i2r_observation_field_0e19c39778_1) < 0 then nat (-2*(i2r_observation_field_0e19c39778_1)-1) else nat (2*(i2r_observation_field_0e19c39778_1))) List.Nil) (List.append (encode_f01d95ec74 (i2r_observation_field_0e19c39778_2)) List.Nil))))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Types_Test.ITree1 :: Types_Test.ITree) ) in (encode_f01d95ec74 (result)))"
end
