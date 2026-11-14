theory Model imports "source/2_functionalprog/Listprog_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Listprog_Test.q1 :: ((int list) \<times> nat)) ) in ((List.length (fst result) # concat (map (\<lambda>v1. [if v1 < 0 then nat (-2*v1-1) else nat (2*v1)]) (fst result))) @ [(snd result)]))"
end
