theory Model imports "source/2_functionalprog/BasicDef_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((BasicDef_Test.case2 :: (nat \<Rightarrow> (char list))) ((((input@[0,1,2,3,4,5,6,7])!0) mod 9))) in (List.length result # concat (map (\<lambda>v0. [(of_char v0 :: nat)]) result)))"
end
