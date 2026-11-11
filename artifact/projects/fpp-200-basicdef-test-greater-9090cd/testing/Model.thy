theory Model imports "source/2_functionalprog/BasicDef_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((BasicDef_Test.greater :: (nat \<Rightarrow> (nat \<Rightarrow> bool))) ((((input@[0,1,2,3,4,5,6,7])!0) mod 9)) ((((input@[0,1,2,3,4,5,6,7])!1) mod 9))) in [if result then 1 else 0])"
end
