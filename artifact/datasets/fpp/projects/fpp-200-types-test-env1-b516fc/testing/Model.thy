theory Model imports "source/2_functionalprog/Types_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Types_Test.env1 :: (nat \<Rightarrow> bool)) ((((input@[0,1,2,3,4,5,6,7])!0) mod 9))) in [if result then 1 else 0])"
end
