theory Model imports "source/2_functionalprog/Function_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Function_Test.arr3 :: ((char list) list)) ) in (List.length result # concat (map (\<lambda>v0. (List.length v0 # concat (map (\<lambda>v1. [(of_char v1 :: nat)]) v0))) result)))"
end
