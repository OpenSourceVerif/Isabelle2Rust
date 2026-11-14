theory Model imports "source/5_IMP/AExp_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((AExp_Test.null_state :: (nat \<Rightarrow> nat)) ((((input@(List.Cons 0 (List.Cons 1 (List.Cons 2 (List.Cons 3 (List.Cons 4 (List.Cons 5 (List.Cons 6 (List.Cons 7 List.Nil)))))))))!0) mod 9))) in [result])"
end
