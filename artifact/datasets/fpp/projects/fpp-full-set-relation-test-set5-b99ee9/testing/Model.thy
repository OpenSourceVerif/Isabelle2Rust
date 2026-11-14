theory Model imports "source/2_functionalprog/Set_Relation_Test" begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Set_Relation_Test.Set5 :: (nat set)) ) in (List.Cons (List.length (List.map (\<lambda>i. ((i) mod 9)) [0..<9])) (List.concat (List.map (\<lambda>p. (List.Cons (if p \<in> (result) then 1 else 0) List.Nil)) (List.map (\<lambda>i. ((i) mod 9)) [0..<9])))))"
end
