theory Model imports "source/2_functionalprog/Types_Test" begin
fun encode_694d09fa51 :: "(int Types_Test.Tree) \<Rightarrow> nat list" where
 "encode_694d09fa51 (Types_Test.Tree.Leaf i2r_observation_field_fbcecebfb3_0) = (List.Cons 0 (List.append (List.Cons (if (i2r_observation_field_fbcecebfb3_0) < 0 then nat (-2*(i2r_observation_field_fbcecebfb3_0)-1) else nat (2*(i2r_observation_field_fbcecebfb3_0))) List.Nil) List.Nil))" |
 "encode_694d09fa51 (Types_Test.Tree.Node i2r_observation_field_fbcecebfb3_0 i2r_observation_field_fbcecebfb3_1 i2r_observation_field_fbcecebfb3_2) = (List.Cons 1 (List.append (encode_694d09fa51 (i2r_observation_field_fbcecebfb3_0)) (List.append (List.Cons (if (i2r_observation_field_fbcecebfb3_1) < 0 then nat (-2*(i2r_observation_field_fbcecebfb3_1)-1) else nat (2*(i2r_observation_field_fbcecebfb3_1))) List.Nil) (List.append (encode_694d09fa51 (i2r_observation_field_fbcecebfb3_2)) List.Nil))))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Types_Test.Tree1 :: (int Types_Test.Tree)) ) in (encode_694d09fa51 (result)))"
end
