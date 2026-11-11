theory Model imports "source/2_functionalprog/Listprog_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Listprog_Test.initq :: (nat \<Rightarrow> ((nat list) \<times> nat))) ((((input@[0,1,2,3,4,5,6,7])!0) mod 9))) in ((List.length (fst result) # concat (map (\<lambda>v1. [v1]) (fst result))) @ [(snd result)]))"
end
