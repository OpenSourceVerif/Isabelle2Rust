theory Model imports "source/2_functionalprog/Function_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Function_Test.arr1 :: (int list)) ) in (List.length result # concat (map (\<lambda>v0. [if v0 < 0 then nat (-2*v0-1) else nat (2*v0)]) result)))"
end
