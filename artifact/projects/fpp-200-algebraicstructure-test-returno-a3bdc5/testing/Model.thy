theory Model imports "source/2_functionalprog/AlgebraicStructure_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((AlgebraicStructure_Test.returno :: (nat \<Rightarrow> (nat option))) ((((input@[0,1,2,3,4,5,6,7])!0) mod 9))) in (case result of None \<Rightarrow> [0] | Some v0 \<Rightarrow> 1 # [v0]))"
end
