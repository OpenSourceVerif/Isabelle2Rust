theory Model imports "source/2_functionalprog/AlgebraicStructure_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((AlgebraicStructure_Test.list2 :: (((char list) list) \<Rightarrow> ((nat \<times> (char list)) list))) ((map (\<lambda>j0. (map (\<lambda>j1. (''abc '' ! (((((input@[0,1,2,3,4,5,6,7])!0)+j0)+j1) mod 4))) [0..<((((input@[0,1,2,3,4,5,6,7])!0)+j0) mod 4)])) [0..<(((input@[0,1,2,3,4,5,6,7])!0) mod 4)]))) in (List.length result # concat (map (\<lambda>v0. ([(fst v0)] @ (List.length (snd v0) # concat (map (\<lambda>v2. [(of_char v2 :: nat)]) (snd v0))))) result)))"
end
