theory Model imports "source/2_functionalprog/Listprog_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Listprog_Test.startsWith :: ((char list) \<Rightarrow> ((char list) \<Rightarrow> bool))) ((map (\<lambda>j0. (''abc '' ! ((((input@[0,1,2,3,4,5,6,7])!0)+j0) mod 4))) [0..<(((input@[0,1,2,3,4,5,6,7])!0) mod 4)])) ((map (\<lambda>j0. (''abc '' ! ((((input@[0,1,2,3,4,5,6,7])!1)+j0) mod 4))) [0..<(((input@[0,1,2,3,4,5,6,7])!1) mod 4)]))) in [if result then 1 else 0])"
end
