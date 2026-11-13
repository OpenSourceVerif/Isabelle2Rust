theory Model imports IntegratedCopyBorrow_Test begin
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedCopyBorrow_Test.list_length ((if (input ! 0) mod 2 = 0 then (MyNil) else (MyCons (input ! 1) ((if (input ! 2) mod 2 = 0 then (MyNil) else (MyCons (input ! 3) ((MyNil) :: (nat my_list)))) :: (nat my_list)))) :: (nat my_list)))"

end
