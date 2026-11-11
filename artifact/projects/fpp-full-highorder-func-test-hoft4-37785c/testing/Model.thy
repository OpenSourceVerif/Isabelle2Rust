theory Model imports "source/2_functionalprog/Highorder_Func_Test" begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Highorder_Func_Test.hoft4 :: ((int \<Rightarrow> int) \<Rightarrow> (int \<Rightarrow> int))) ((\<lambda>arg4739e00b09. (int ((((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0)) + sum_list ((List.Cons (if (arg4739e00b09) < 0 then nat (-2*(arg4739e00b09)-1) else nat (2*(arg4739e00b09))) List.Nil))) mod 9) - 4))) ((int (((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 1)) mod 9) - 4))) in (List.Cons (if (result) < 0 then nat (-2*(result)-1) else nat (2*(result))) List.Nil))"
end
