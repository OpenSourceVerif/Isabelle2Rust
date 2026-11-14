theory Model imports "source/2_functionalprog/Types_Test" begin
fun encode_f3715f18d4 :: "((char list) Types_Test.array) \<Rightarrow> nat list" where
 "encode_f3715f18d4 (Types_Test.array.Null ) = (List.Cons 0 List.Nil)" |
 "encode_f3715f18d4 (Types_Test.array.Conn i2r_observation_field_914093ac3f_0 i2r_observation_field_914093ac3f_1) = (List.Cons 1 (List.append (List.Cons (List.length (i2r_observation_field_914093ac3f_0)) (List.concat (List.map (\<lambda>v. (List.Cons ((of_char (v) :: nat)) List.Nil)) (i2r_observation_field_914093ac3f_0)))) (List.append (encode_f3715f18d4 (i2r_observation_field_914093ac3f_1)) List.Nil)))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Types_Test.arr2 :: ((char list) Types_Test.array)) ) in (encode_f3715f18d4 (result)))"
end
