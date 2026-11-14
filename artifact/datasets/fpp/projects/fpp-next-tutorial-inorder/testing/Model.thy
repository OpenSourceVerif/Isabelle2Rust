theory Model imports Tutorial_Test begin
primrec fixture :: "nat list \<Rightarrow> nat Tutorial_Test.tree" where
 "fixture [] = Tutorial_Test.Leaf" | "fixture (x#xs) = Tutorial_Test.Branch (fixture xs) x Tutorial_Test.Leaf"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Tutorial_Test.inorder (fixture input)"
end
