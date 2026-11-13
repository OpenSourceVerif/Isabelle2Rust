theory Model imports IntegratedTree_Test begin
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (IntegratedTree_Test.ftree_height ((if (input ! 0) mod 2 = 0 then (FTLeaf ((Flags ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: flag_pair)) else (FTNode ((if (input ! 4) mod 2 = 0 then (FTLeaf ((Flags ((input ! 6) mod 2 = 0) ((input ! 7) mod 2 = 0)) :: flag_pair)) else (FTNode ((FTLeaf ((Flags ((input ! 2) mod 2 = 0) ((input ! 3) mod 2 = 0)) :: flag_pair)) :: flag_tree) ((Flags ((input ! 5) mod 2 = 0) ((input ! 6) mod 2 = 0)) :: flag_pair) ((FTLeaf ((Flags ((input ! 1) mod 2 = 0) ((input ! 2) mod 2 = 0)) :: flag_pair)) :: flag_tree))) :: flag_tree) ((Flags ((input ! 4) mod 2 = 0) ((input ! 5) mod 2 = 0)) :: flag_pair) ((if (input ! 6) mod 2 = 0 then (FTLeaf ((Flags ((input ! 0) mod 2 = 0) ((input ! 1) mod 2 = 0)) :: flag_pair)) else (FTNode ((FTLeaf ((Flags ((input ! 4) mod 2 = 0) ((input ! 5) mod 2 = 0)) :: flag_pair)) :: flag_tree) ((Flags ((input ! 7) mod 2 = 0) ((input ! 0) mod 2 = 0)) :: flag_pair) ((FTLeaf ((Flags ((input ! 3) mod 2 = 0) ((input ! 4) mod 2 = 0)) :: flag_pair)) :: flag_tree))) :: flag_tree))) :: flag_tree))"

end
