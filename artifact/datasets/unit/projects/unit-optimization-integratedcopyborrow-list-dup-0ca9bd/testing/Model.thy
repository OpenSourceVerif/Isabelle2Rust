theory Model imports IntegratedCopyBorrow_Test begin
fun i2r_encode_2 :: "nat \<Rightarrow> nat list" where
"i2r_encode_2 x = [x]"

fun i2r_encode_1 :: "(nat my_list) \<Rightarrow> nat list" where
"i2r_encode_1 (MyNil) = [0]"
| "i2r_encode_1 (MyCons x0 x1) = [1] @ i2r_encode_2 (x0) @ i2r_encode_1 (x1)"

fun i2r_encode_0 :: "((nat my_list) \<times> (nat my_list)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedCopyBorrow_Test.list_dup ((if (input ! 0) mod 2 = 0 then (MyNil) else (MyCons (input ! 1) ((if (input ! 2) mod 2 = 0 then (MyNil) else (MyCons (input ! 3) ((MyNil) :: (nat my_list)))) :: (nat my_list)))) :: (nat my_list)))"

end
