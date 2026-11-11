theory Model imports "source/2_functionalprog/AlgebraicStructure_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((AlgebraicStructure_Test.eval :: int) ) in [if result < 0 then nat (-2*result-1) else nat (2*result)])"
end
