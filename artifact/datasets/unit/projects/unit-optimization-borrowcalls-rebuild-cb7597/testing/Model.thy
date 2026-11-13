theory Model imports BorrowCalls_Test begin
fun i2r_encode_1 :: "bool \<Rightarrow> nat list" where
"i2r_encode_1 x = [if x then 1 else 0]"

fun i2r_encode_0 :: "tree \<Rightarrow> nat list" where
"i2r_encode_0 (Leaf x0) = [0] @ i2r_encode_1 (x0)"
| "i2r_encode_0 (Branch x0 x1) = [1] @ i2r_encode_0 (x0) @ i2r_encode_0 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BorrowCalls_Test.rebuild ((if (input ! 0) mod 2 = 0 then (Leaf ((input ! 1) mod 2 = 0)) else (Branch ((if (input ! 2) mod 2 = 0 then (Leaf ((input ! 3) mod 2 = 0)) else (Branch ((Leaf ((input ! 5) mod 2 = 0)) :: tree) ((Leaf ((input ! 7) mod 2 = 0)) :: tree))) :: tree) ((if (input ! 0) mod 2 = 0 then (Leaf ((input ! 1) mod 2 = 0)) else (Branch ((Leaf ((input ! 3) mod 2 = 0)) :: tree) ((Leaf ((input ! 5) mod 2 = 0)) :: tree))) :: tree))) :: tree))"

end
