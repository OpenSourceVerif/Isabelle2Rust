theory Model imports Types_Test begin
primrec fixture :: "nat list \<Rightarrow> nat Types_Test.Tree" where
 "fixture [] = Types_Test.Tree.Leaf 0" |
 "fixture (x#xs) = Types_Test.Tree.Node (fixture xs) x (Types_Test.Tree.Leaf (List.length xs))"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [Types_Test.count (fixture input)]"
end
