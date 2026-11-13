theory Model imports BorrowCalls_Test begin
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (BorrowCalls_Test.bbox_get ((BorrowBox (input ! 1)) :: (nat borrow_box)))"

end
