theory Model imports IntegratedCopyBorrow_Test begin
fun i2r_encode_1 :: "nat \<Rightarrow> nat list" where
"i2r_encode_1 x = [x]"

fun i2r_encode_0 :: "(nat my_list) \<Rightarrow> nat list" where
"i2r_encode_0 (MyNil) = [0]"
| "i2r_encode_0 (MyCons x0 x1) = [1] @ i2r_encode_1 (x0) @ i2r_encode_0 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedCopyBorrow_Test.list_append ((if (input ! 0) mod 2 = 0 then (MyNil) else (MyCons (input ! 1) ((if (input ! 2) mod 2 = 0 then (MyNil) else (MyCons (input ! 3) ((MyNil) :: (nat my_list)))) :: (nat my_list)))) :: (nat my_list)) ((if (input ! 5) mod 2 = 0 then (MyNil) else (MyCons (input ! 6) ((if (input ! 7) mod 2 = 0 then (MyNil) else (MyCons (input ! 0) ((MyNil) :: (nat my_list)))) :: (nat my_list)))) :: (nat my_list)))"

end
