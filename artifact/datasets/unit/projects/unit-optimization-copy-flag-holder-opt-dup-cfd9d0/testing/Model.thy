theory Model imports Copy_Test begin
fun i2r_encode_3 :: "bool \<Rightarrow> nat list" where
"i2r_encode_3 x = [if x then 1 else 0]"

fun i2r_encode_2 :: "flag_holder \<Rightarrow> nat list" where
"i2r_encode_2 (FlagHolder x0 x1) = [0] @ i2r_encode_3 (x0) @ i2r_encode_3 (x1)"

fun i2r_encode_1 :: "(flag_holder opt_val) \<Rightarrow> nat list" where
"i2r_encode_1 (OptNone) = [0]"
| "i2r_encode_1 (OptSome x0) = [1] @ i2r_encode_2 (x0)"

fun i2r_encode_0 :: "((flag_holder opt_val) \<times> (flag_holder opt_val)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Copy_Test.flag_holder_opt_dup ((if (input ! 0) mod 2 = 0 then (OptNone) else (OptSome ((FlagHolder ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: flag_holder))) :: (flag_holder opt_val)))"

end
