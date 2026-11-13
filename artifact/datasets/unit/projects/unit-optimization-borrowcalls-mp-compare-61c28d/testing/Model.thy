theory Model imports BorrowCalls_Test begin
fun i2r_encode_0 :: "bool \<Rightarrow> nat list" where
"i2r_encode_0 x = [if x then 1 else 0]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BorrowCalls_Test.mp_compare ((if (input ! 0) mod 2 = 0 then (MPLeaf ((input ! 1) mod 2 = 0)) else (MPNode ((if (input ! 2) mod 2 = 0 then (MPLeaf ((input ! 3) mod 2 = 0)) else (MPNode ((MPLeaf ((input ! 5) mod 2 = 0)) :: mp_tree) ((MPLeaf ((input ! 7) mod 2 = 0)) :: mp_tree))) :: mp_tree) ((if (input ! 0) mod 2 = 0 then (MPLeaf ((input ! 1) mod 2 = 0)) else (MPNode ((MPLeaf ((input ! 3) mod 2 = 0)) :: mp_tree) ((MPLeaf ((input ! 5) mod 2 = 0)) :: mp_tree))) :: mp_tree))) :: mp_tree) ((if (input ! 6) mod 2 = 0 then (MPLeaf ((input ! 7) mod 2 = 0)) else (MPNode ((if (input ! 0) mod 2 = 0 then (MPLeaf ((input ! 1) mod 2 = 0)) else (MPNode ((MPLeaf ((input ! 3) mod 2 = 0)) :: mp_tree) ((MPLeaf ((input ! 5) mod 2 = 0)) :: mp_tree))) :: mp_tree) ((if (input ! 6) mod 2 = 0 then (MPLeaf ((input ! 7) mod 2 = 0)) else (MPNode ((MPLeaf ((input ! 1) mod 2 = 0)) :: mp_tree) ((MPLeaf ((input ! 3) mod 2 = 0)) :: mp_tree))) :: mp_tree))) :: mp_tree))"

end
