theory Model imports "source/2_functionalprog/BasicDef_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((BasicDef_Test.cst3 :: int) ) in [if result < 0 then nat (-2*result-1) else nat (2*result)])"
end
