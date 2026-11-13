theory Model imports IntegratedCopyBorrow_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedCopyBorrow_Test.list_is_empty ((if (input ! 0) mod 2 = 0 then (MyNil) else (MyCons (input ! 1) ((if (input ! 2) mod 2 = 0 then (MyNil) else (MyCons (input ! 3) ((MyNil) :: (nat my_list)))) :: (nat my_list)))) :: (nat my_list)))"

end
