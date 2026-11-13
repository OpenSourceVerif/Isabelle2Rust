theory Model imports IntegratedCopyBorrow_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedCopyBorrow_Test.list_head ((if (input ! 0) mod 2 = 0 then (MyNil) else (MyCons ((input ! 1) mod 2 = 0) ((if (input ! 2) mod 2 = 0 then (MyNil) else (MyCons ((input ! 3) mod 2 = 0) ((MyNil) :: (bool my_list)))) :: (bool my_list)))) :: (bool my_list)))"

end
