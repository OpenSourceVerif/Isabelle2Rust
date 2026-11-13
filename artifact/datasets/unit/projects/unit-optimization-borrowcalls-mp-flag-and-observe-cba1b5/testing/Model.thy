theory Model imports BorrowCalls_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BorrowCalls_Test.mp_flag_and_observe ((input ! 0) mod 2 = 0) ((if (input ! 1) mod 2 = 0 then (MPLeaf ((input ! 2) mod 2 = 0)) else (MPNode ((if (input ! 3) mod 2 = 0 then (MPLeaf ((input ! 4) mod 2 = 0)) else (MPNode ((MPLeaf ((input ! 6) mod 2 = 0)) :: mp_tree) ((MPLeaf ((input ! 0) mod 2 = 0)) :: mp_tree))) :: mp_tree) ((if (input ! 1) mod 2 = 0 then (MPLeaf ((input ! 2) mod 2 = 0)) else (MPNode ((MPLeaf ((input ! 4) mod 2 = 0)) :: mp_tree) ((MPLeaf ((input ! 6) mod 2 = 0)) :: mp_tree))) :: mp_tree))) :: mp_tree))"

end
