theory Model imports "source/2_functionalprog/BasicDef_Test" begin
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((BasicDef_Test.test :: (int \<Rightarrow> (int option))) ((int (((input@(List.Cons 0 (List.Cons 1 (List.Cons 2 (List.Cons 3 (List.Cons 4 (List.Cons 5 (List.Cons 6 (List.Cons 7 List.Nil)))))))))!0) mod 9) - 4))) in (case result of None \<Rightarrow> [0] | Some v0 \<Rightarrow> 1 # [if v0 < 0 then nat (-2*v0-1) else nat (2*v0)]))"
end
