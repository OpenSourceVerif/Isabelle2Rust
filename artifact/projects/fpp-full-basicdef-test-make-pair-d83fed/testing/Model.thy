theory Model imports "source/2_functionalprog/BasicDef_Test" begin

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((BasicDef_Test.make_pair :: (int \<Rightarrow> ((int \<Rightarrow> int) \<times> int))) ((int (((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0)) mod 9) - 4))) in (List.append (List.Cons (List.length (List.map (\<lambda>i. (int ((i) mod 9) - 4)) [0..<9])) (List.concat (List.map (\<lambda>p. (List.Cons (if ((((fst (result))) p)) < 0 then nat (-2*((((fst (result))) p))-1) else nat (2*((((fst (result))) p)))) List.Nil)) (List.map (\<lambda>i. (int ((i) mod 9) - 4)) [0..<9])))) (List.Cons (if ((snd (result))) < 0 then nat (-2*((snd (result)))-1) else nat (2*((snd (result))))) List.Nil)))"
end
