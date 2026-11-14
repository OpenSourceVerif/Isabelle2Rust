theory Model imports "source/2_functionalprog/Types_Test" begin
fun encode_c257c3c5be :: "(int Types_Test.array) \<Rightarrow> nat list" where
 "encode_c257c3c5be (Types_Test.array.Null ) = (List.Cons 0 List.Nil)" |
 "encode_c257c3c5be (Types_Test.array.Conn i2r_observation_field_c451ed4953_0 i2r_observation_field_c451ed4953_1) = (List.Cons 1 (List.append (List.Cons (if (i2r_observation_field_c451ed4953_0) < 0 then nat (-2*(i2r_observation_field_c451ed4953_0)-1) else nat (2*(i2r_observation_field_c451ed4953_0))) List.Nil) (List.append (encode_c257c3c5be (i2r_observation_field_c451ed4953_1)) List.Nil)))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Types_Test.arr1 :: (int Types_Test.array)) ) in (encode_c257c3c5be (result)))"
end
