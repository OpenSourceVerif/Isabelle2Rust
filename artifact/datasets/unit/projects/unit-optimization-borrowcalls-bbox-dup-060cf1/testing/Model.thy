theory Model imports BorrowCalls_Test begin
fun i2r_encode_2 :: "nat \<Rightarrow> nat list" where
"i2r_encode_2 x = [x]"

fun i2r_encode_1 :: "(nat borrow_box) \<Rightarrow> nat list" where
"i2r_encode_1 (BorrowBox x0) = [0] @ i2r_encode_2 (x0)"

fun i2r_encode_0 :: "((nat borrow_box) \<times> (nat borrow_box)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BorrowCalls_Test.bbox_dup ((BorrowBox (input ! 1)) :: (nat borrow_box)))"

end
