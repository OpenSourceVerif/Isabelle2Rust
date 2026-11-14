theory Model imports Tutorial_Test begin
primrec fixture :: "nat list \<Rightarrow> nat Tutorial_Test.tree" where
 "fixture [] = Tutorial_Test.Leaf" | "fixture (x#xs) = Tutorial_Test.Branch (fixture xs) x Tutorial_Test.Leaf"
fun encode_tree :: "nat Tutorial_Test.tree \<Rightarrow> nat list" where
 "encode_tree Tutorial_Test.Leaf = [0]" |
 "encode_tree (Tutorial_Test.Branch l x r) = [1,x] @ encode_tree l @ encode_tree r"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = encode_tree (Tutorial_Test.mirror (fixture input))"
end
