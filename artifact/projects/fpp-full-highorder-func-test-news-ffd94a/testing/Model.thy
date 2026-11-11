theory Model imports "source/2_functionalprog/Highorder_Func_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Highorder_Func_Test.news :: (((char list) list) list)) ) in (List.length result # concat (map (\<lambda>v0. (List.length v0 # concat (map (\<lambda>v1. (List.length v1 # concat (map (\<lambda>v2. [(of_char v2 :: nat)]) v1))) v0))) result)))"
end
