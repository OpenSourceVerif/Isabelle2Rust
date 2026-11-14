theory Model imports AVL_Set_Code_Test begin

primrec structural_fixture :: "nat list \<Rightarrow> (nat * nat) Tree_Test.tree" where
 "structural_fixture [] = Tree_Test.Leaf" |
 "structural_fixture (x#xs) = (let t = structural_fixture xs in Tree_Test.Node t (x, Suc (Tree_Test.height t)) Tree_Test.Leaf)"
fun encode_tree :: "(nat * nat) Tree_Test.tree \<Rightarrow> nat list" where
 "encode_tree Tree_Test.Leaf = [0]" |
 "encode_tree (Tree_Test.Node l (x,h) r) = [1,x,h] @ encode_tree l @ encode_tree r"

definition valid_fixture :: "nat list \<Rightarrow> (nat*nat) Tree_Test.tree" where
 "valid_fixture xs = fold AVL_Set_Code_Test.insert xs Tree_Test.Leaf"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = encode_tree (AVL_Set_Code_Test.delete (hd(input@[0])) (valid_fixture input))"
end
