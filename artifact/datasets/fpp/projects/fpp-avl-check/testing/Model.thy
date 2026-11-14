theory Model imports AVL_Set_Test begin

primrec fixture :: "nat list \<Rightarrow> (nat * nat) Tree_Test.tree" where
 "fixture [] = Tree_Test.Leaf" |
 "fixture (x#xs) = (let t = fixture xs in Tree_Test.Node t (x, Suc (Tree_Test.height t)) Tree_Test.Leaf)"
fun encode_tree :: "(nat * nat) Tree_Test.tree \<Rightarrow> nat list" where
 "encode_tree Tree_Test.Leaf = [0]" |
 "encode_tree (Tree_Test.Node l (x,h) r) = [1,x,h] @ encode_tree l @ encode_tree r"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [if AVL_Set_Test.avl (fixture input) then 1 else 0]"
end
