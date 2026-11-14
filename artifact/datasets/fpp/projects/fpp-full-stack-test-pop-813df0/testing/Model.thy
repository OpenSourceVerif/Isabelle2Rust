theory Model imports "source/4_ds_algo/Stack_Queue/stack_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((stack_Test.pop :: ((nat list) \<Rightarrow> (nat \<times> (nat list)))) ((List.Cons 0 (map (\<lambda>j0. ((((input@(List.Cons 0 (List.Cons 1 (List.Cons 2 (List.Cons 3 (List.Cons 4 (List.Cons 5 (List.Cons 6 (List.Cons 7 List.Nil)))))))))!0)+j0) mod 9)) [0..<(((input@(List.Cons 0 (List.Cons 1 (List.Cons 2 (List.Cons 3 (List.Cons 4 (List.Cons 5 (List.Cons 6 (List.Cons 7 List.Nil)))))))))!0) mod 4)])))) in ([(fst result)] @ (List.length (snd result) # concat (map (\<lambda>v1. [v1]) (snd result)))))"
end
