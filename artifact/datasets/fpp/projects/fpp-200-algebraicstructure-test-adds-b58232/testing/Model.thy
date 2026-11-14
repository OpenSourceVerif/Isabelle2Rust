theory Model imports "source/2_functionalprog/AlgebraicStructure_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((AlgebraicStructure_Test.adds :: ((int option) \<Rightarrow> (int option))) ((if ((input@[0,1,2,3,4,5,6,7])!0) mod 3 = 0 then None else Some ((int (((input@[0,1,2,3,4,5,6,7])!0) mod 9) - 4))))) in (case result of None \<Rightarrow> [0] | Some v0 \<Rightarrow> 1 # [if v0 < 0 then nat (-2*v0-1) else nat (2*v0)]))"
end
