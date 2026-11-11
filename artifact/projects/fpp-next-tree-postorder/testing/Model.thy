theory Model imports Tree_Test begin

fun fixture :: "nat list \<Rightarrow> nat Tree_Test.tree" where
 "fixture [] = Tree_Test.Leaf" |
 "fixture [x] = Tree_Test.Node Tree_Test.Leaf x Tree_Test.Leaf" |
 "fixture (x#y#xs) = Tree_Test.Node (fixture xs) x (Tree_Test.Node Tree_Test.Leaf y Tree_Test.Leaf)"
fun encode_tree :: "nat Tree_Test.tree \<Rightarrow> nat list" where
 "encode_tree Tree_Test.Leaf = [0]" |
 "encode_tree (Tree_Test.Node l x r) = [1,x] @ encode_tree l @ encode_tree r"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = Tree_Test.postorder (fixture input)"
end
