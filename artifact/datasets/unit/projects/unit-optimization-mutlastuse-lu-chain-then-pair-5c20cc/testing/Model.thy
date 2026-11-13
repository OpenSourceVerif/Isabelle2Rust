theory Model imports MutLastUse_Test begin
fun i2r_encode_2 :: "bool \<Rightarrow> nat list" where
"i2r_encode_2 x = [if x then 1 else 0]"

fun i2r_encode_1 :: "lu_tree \<Rightarrow> nat list" where
"i2r_encode_1 (LULeaf x0) = [0] @ i2r_encode_2 (x0)"
| "i2r_encode_1 (LUNode x0 x1) = [1] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

fun i2r_encode_0 :: "(lu_tree \<times> lu_tree) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (MutLastUse_Test.lu_chain_then_pair ((if (input ! 0) mod 2 = 0 then (LULeaf ((input ! 1) mod 2 = 0)) else (LUNode ((if (input ! 2) mod 2 = 0 then (LULeaf ((input ! 3) mod 2 = 0)) else (LUNode ((LULeaf ((input ! 5) mod 2 = 0)) :: lu_tree) ((LULeaf ((input ! 7) mod 2 = 0)) :: lu_tree))) :: lu_tree) ((if (input ! 0) mod 2 = 0 then (LULeaf ((input ! 1) mod 2 = 0)) else (LUNode ((LULeaf ((input ! 3) mod 2 = 0)) :: lu_tree) ((LULeaf ((input ! 5) mod 2 = 0)) :: lu_tree))) :: lu_tree))) :: lu_tree))"

end
