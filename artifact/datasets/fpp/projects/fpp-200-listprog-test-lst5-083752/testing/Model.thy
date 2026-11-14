theory Model imports "source/2_functionalprog/Listprog_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Listprog_Test.lst5 :: (nat list)) ) in (List.length result # concat (map (\<lambda>v0. [v0]) result)))"
end
