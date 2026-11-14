theory Model imports Leftist_Heap_Test begin
primrec heap_chain :: "nat list \<Rightarrow> (nat*nat) Tree_Test.tree" where
 "heap_chain [] = Tree_Test.Leaf" |
 "heap_chain (x#xs) = Tree_Test.Node (heap_chain xs) (x,1) Tree_Test.Leaf"
definition fixture :: "nat list \<Rightarrow> (nat*nat) Tree_Test.tree" where
 "fixture xs = heap_chain (sort xs)"
fun encode_tree :: "(nat*nat) Tree_Test.tree \<Rightarrow> nat list" where
 "encode_tree Tree_Test.Leaf = [0]" |
 "encode_tree (Tree_Test.Node l (x,h) r) = [1,x,h] @ encode_tree l @ encode_tree r"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = encode_tree (Leftist_Heap_Test.insert (List.length input) (fixture input))"
end
