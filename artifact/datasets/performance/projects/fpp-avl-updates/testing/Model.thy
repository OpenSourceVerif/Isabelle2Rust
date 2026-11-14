theory Model imports AVL_Set_Code_Test begin
definition fixture :: "nat list => nat tree_ht * nat list" where
  "fixture input = (let k=hd (input@[0]); data=tl input in
    (fold AVL_Set_Code_Test.insert (take k data) Tree_Test.Leaf, drop k data))"
definition step :: "nat => nat tree_ht => nat tree_ht" where
  "step w t = (if even w then AVL_Set_Code_Test.insert (w div 2) t else AVL_Set_Code_Test.delete (w div 2) t)"
fun encode_tree :: "nat tree_ht => nat list" where
  "encode_tree Tree_Test.Leaf = [0]" |
  "encode_tree (Tree_Test.Node l (x,h) r) = [1,x,h] @ encode_tree l @ encode_tree r"
definition observe :: "nat list => nat list" where
  "observe input = encode_tree (fold step (snd (fixture input)) (fst (fixture input)))"
end
