theory Model imports "source/2_functionalprog/Highorder_Func_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Highorder_Func_Test.concat2c' :: ((char list) \<Rightarrow> ((char list) \<Rightarrow> (char list)))) ((map (\<lambda>j0. (''abc '' ! ((((input@[0,1,2,3,4,5,6,7])!0)+j0) mod 4))) [0..<(((input@[0,1,2,3,4,5,6,7])!0) mod 4)])) ((map (\<lambda>j0. (''abc '' ! ((((input@[0,1,2,3,4,5,6,7])!1)+j0) mod 4))) [0..<(((input@[0,1,2,3,4,5,6,7])!1) mod 4)]))) in (List.length result # concat (map (\<lambda>v0. [(of_char v0 :: nat)]) result)))"
end
