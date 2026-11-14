theory Model imports "source/2_functionalprog/BasicDef_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((BasicDef_Test.if1 :: (bool \<Rightarrow> (char list))) ((((input@(List.Cons 0 (List.Cons 1 (List.Cons 2 (List.Cons 3 (List.Cons 4 (List.Cons 5 (List.Cons 6 (List.Cons 7 List.Nil)))))))))!0) mod 2 = 0))) in (List.length result # concat (map (\<lambda>v0. [(of_char v0 :: nat)]) result)))"
end
