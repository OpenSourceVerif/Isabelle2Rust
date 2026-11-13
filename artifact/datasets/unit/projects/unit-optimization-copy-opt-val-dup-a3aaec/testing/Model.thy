theory Model imports Copy_Test begin
fun i2r_encode_2 :: "nat \<Rightarrow> nat list" where
"i2r_encode_2 x = [x]"

fun i2r_encode_1 :: "(nat opt_val) \<Rightarrow> nat list" where
"i2r_encode_1 (OptNone) = [0]"
| "i2r_encode_1 (OptSome x0) = [1] @ i2r_encode_2 (x0)"

fun i2r_encode_0 :: "((nat opt_val) \<times> (nat opt_val)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Copy_Test.opt_val_dup ((if (input ! 0) mod 2 = 0 then (OptNone) else (OptSome (input ! 1))) :: (nat opt_val)))"

end
