theory Model imports "source/2_functionalprog/AlgebraicStructure_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((AlgebraicStructure_Test.returnl :: (nat \<Rightarrow> (nat list))) ((((input@[0,1,2,3,4,5,6,7])!0) mod 9))) in (List.length result # concat (map (\<lambda>v0. [v0]) result)))"
end
