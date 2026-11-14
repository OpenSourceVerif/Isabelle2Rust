theory Model imports "source/4_ds_algo/Stack_Queue/Queue_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Queue_Test.dequeue_list :: ((nat list) \<Rightarrow> (nat list))) ((map (\<lambda>j0. ((((input@(List.Cons 0 (List.Cons 1 (List.Cons 2 (List.Cons 3 (List.Cons 4 (List.Cons 5 (List.Cons 6 (List.Cons 7 List.Nil)))))))))!0)+j0) mod 9)) [0..<(((input@(List.Cons 0 (List.Cons 1 (List.Cons 2 (List.Cons 3 (List.Cons 4 (List.Cons 5 (List.Cons 6 (List.Cons 7 List.Nil)))))))))!0) mod 4)]))) in (List.length result # concat (map (\<lambda>v0. [v0]) result)))"
end
