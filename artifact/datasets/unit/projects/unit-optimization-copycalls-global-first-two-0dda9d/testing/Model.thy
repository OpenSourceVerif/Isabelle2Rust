theory Model imports CopyCalls_Test begin
fun i2r_encode_2 :: "bool \<Rightarrow> nat list" where
"i2r_encode_2 x = [if x then 1 else 0]"

fun i2r_encode_1 :: "global_char \<Rightarrow> nat list" where
"i2r_encode_1 (GlobalChar x0 x1) = [0] @ i2r_encode_2 (x0) @ i2r_encode_2 (x1)"

fun i2r_encode_0 :: "(global_char \<times> global_char) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (CopyCalls_Test.global_first_two ((if (input ! 0) mod 2 = 0 then (GlobalNil) else (GlobalCons ((GlobalChar ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: global_char) ((if (input ! 4) mod 2 = 0 then (GlobalNil) else (GlobalCons ((GlobalChar ((input ! 6) mod 2 = 0) ((input ! 7) mod 2 = 0)) :: global_char) ((GlobalNil) :: (global_char global_list)))) :: (global_char global_list)))) :: (global_char global_list)))"

end
