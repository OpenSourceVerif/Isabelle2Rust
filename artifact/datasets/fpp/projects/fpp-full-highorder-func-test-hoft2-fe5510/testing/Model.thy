theory Model imports "source/2_functionalprog/Highorder_Func_Test" begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Highorder_Func_Test.hoft2 :: (((int \<Rightarrow> int) \<Rightarrow> int) \<Rightarrow> int)) ((\<lambda>argf67c3481b0. (int ((((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0)) + sum_list ((List.Cons (List.length (List.map (\<lambda>i. (int ((i) mod 9) - 4)) [0..<9])) (List.concat (List.map (\<lambda>p. (List.Cons (if (((argf67c3481b0) p)) < 0 then nat (-2*(((argf67c3481b0) p))-1) else nat (2*(((argf67c3481b0) p)))) List.Nil)) (List.map (\<lambda>i. (int ((i) mod 9) - 4)) [0..<9])))))) mod 9) - 4)))) in (List.Cons (if (result) < 0 then nat (-2*(result)-1) else nat (2*(result))) List.Nil))"
end
