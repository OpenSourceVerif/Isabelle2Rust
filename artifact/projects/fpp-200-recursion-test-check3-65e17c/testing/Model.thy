theory Model imports "source/2_functionalprog/Recursion_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Recursion_Test.check3 :: ((char list) \<Rightarrow> bool)) ((if (input@[0])!0 mod 2 = 0 then ''good'' else ''bad''))) in [if result then 1 else 0])"
end
