theory Model imports "source/2_functionalprog/Recursion_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Recursion_Test.first :: ((nat \<times> nat) \<Rightarrow> nat)) (((((input@[0,1,2,3,4,5,6,7])!0) mod 9),((((input@[0,1,2,3,4,5,6,7])!0)+1) mod 9)))) in [result])"
end
