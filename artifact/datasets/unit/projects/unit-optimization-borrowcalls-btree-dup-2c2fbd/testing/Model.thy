theory Model imports BorrowCalls_Test begin
fun i2r_encode_2 :: "bool \<Rightarrow> nat list" where
"i2r_encode_2 x = [if x then 1 else 0]"

fun i2r_encode_1 :: "borrow_tree \<Rightarrow> nat list" where
"i2r_encode_1 (BLeaf x0) = [0] @ i2r_encode_2 (x0)"
| "i2r_encode_1 (BNode x0 x1) = [1] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

fun i2r_encode_0 :: "(borrow_tree \<times> borrow_tree) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BorrowCalls_Test.btree_dup ((if (input ! 0) mod 2 = 0 then (BLeaf ((input ! 1) mod 2 = 0)) else (BNode ((if (input ! 2) mod 2 = 0 then (BLeaf ((input ! 3) mod 2 = 0)) else (BNode ((BLeaf ((input ! 5) mod 2 = 0)) :: borrow_tree) ((BLeaf ((input ! 7) mod 2 = 0)) :: borrow_tree))) :: borrow_tree) ((if (input ! 0) mod 2 = 0 then (BLeaf ((input ! 1) mod 2 = 0)) else (BNode ((BLeaf ((input ! 3) mod 2 = 0)) :: borrow_tree) ((BLeaf ((input ! 5) mod 2 = 0)) :: borrow_tree))) :: borrow_tree))) :: borrow_tree))"

end
