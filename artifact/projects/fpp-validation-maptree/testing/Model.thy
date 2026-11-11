theory Model imports AlgebraicStructure_Test begin

primrec fixture :: "nat list \<Rightarrow> nat AlgebraicStructure_Test.tree" where
 "fixture [] = AlgebraicStructure_Test.Leaf 0" |
 "fixture (x#xs) = AlgebraicStructure_Test.Node (AlgebraicStructure_Test.Leaf x) (fixture xs)"
fun encode_tree :: "nat AlgebraicStructure_Test.tree \<Rightarrow> nat list" where
 "encode_tree (AlgebraicStructure_Test.Leaf x) = [0,x]" |
 "encode_tree (AlgebraicStructure_Test.Node l r) = [1] @ encode_tree l @ encode_tree r"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = encode_tree (AlgebraicStructure_Test.maptree (\<lambda>x::nat. Suc x) (fixture input))"
end
