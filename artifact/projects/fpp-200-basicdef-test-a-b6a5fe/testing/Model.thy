theory Model imports "source/2_functionalprog/BasicDef_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((BasicDef_Test.A :: bool) ) in [if result then 1 else 0])"
end
