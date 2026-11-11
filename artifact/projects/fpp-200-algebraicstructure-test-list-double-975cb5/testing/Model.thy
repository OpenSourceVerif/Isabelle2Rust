theory Model imports "source/2_functionalprog/AlgebraicStructure_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((AlgebraicStructure_Test.list_double :: ((nat list) \<Rightarrow> (nat list))) ((map (\<lambda>j0. ((((input@[0,1,2,3,4,5,6,7])!0)+j0) mod 9)) [0..<(((input@[0,1,2,3,4,5,6,7])!0) mod 4)]))) in (List.length result # concat (map (\<lambda>v0. [v0]) result)))"
end
