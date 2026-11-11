theory Model imports Tree_Test begin
primrec fixture :: "nat list \<Rightarrow> nat Tree_Test.tree" where
"fixture [] = Tree_Test.Leaf" | "fixture (x#xs) = Tree_Test.Node (fixture xs) x Tree_Test.Leaf"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Tree_Test.preorder (Tree_Test.mirror (fixture input))"
end
