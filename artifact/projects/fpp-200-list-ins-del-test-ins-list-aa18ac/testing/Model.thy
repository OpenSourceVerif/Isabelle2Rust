theory Model imports "source/4_ds_algo/bintree/List_Ins_Del_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((List_Ins_Del_Test.ins_list :: (nat \<Rightarrow> ((nat list) \<Rightarrow> (nat list)))) ((((input@[0,1,2,3,4,5,6,7])!0) mod 9)) ((sort (map (\<lambda>j0. ((((input@[0,1,2,3,4,5,6,7])!1)+j0) mod 9)) [0..<(((input@[0,1,2,3,4,5,6,7])!1) mod 4)])))) in (List.length result # concat (map (\<lambda>v0. [v0]) result)))"
end
