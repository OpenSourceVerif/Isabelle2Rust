theory Model imports "source/1_Intro/func_imp_compare_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((func_imp_compare_Test.insert :: (int \<Rightarrow> ((int list) \<Rightarrow> (int list)))) ((int (((input@[0,1,2,3,4,5,6,7])!0) mod 9) - 4)) ((sort (map (\<lambda>j0. (int ((((input@[0,1,2,3,4,5,6,7])!1)+j0) mod 9) - 4)) [0..<(((input@[0,1,2,3,4,5,6,7])!1) mod 4)])))) in (List.length result # concat (map (\<lambda>v0. [if v0 < 0 then nat (-2*v0-1) else nat (2*v0)]) result)))"
end
