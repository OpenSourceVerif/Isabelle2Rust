theory Model imports "source/2_functionalprog/Listprog_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Listprog_Test.search :: ((nat list) \<Rightarrow> (nat \<Rightarrow> int))) ((map (\<lambda>j0. ((((input@(List.Cons 0 (List.Cons 1 (List.Cons 2 (List.Cons 3 (List.Cons 4 (List.Cons 5 (List.Cons 6 (List.Cons 7 List.Nil)))))))))!0)+j0) mod 9)) [0..<(((input@(List.Cons 0 (List.Cons 1 (List.Cons 2 (List.Cons 3 (List.Cons 4 (List.Cons 5 (List.Cons 6 (List.Cons 7 List.Nil)))))))))!0) mod 4)])) ((((input@(List.Cons 0 (List.Cons 1 (List.Cons 2 (List.Cons 3 (List.Cons 4 (List.Cons 5 (List.Cons 6 (List.Cons 7 List.Nil)))))))))!1) mod 9))) in [if result < 0 then nat (-2*result-1) else nat (2*result)])"
end
