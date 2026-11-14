theory Model imports "source/2_functionalprog/Classes_Test" begin
definition fixture_9267ab675f_2 :: "nat \<Rightarrow> Classes_Test.Number" where
 "fixture_9267ab675f_2 s = (if s mod 3 = 0 then (Classes_Test.Number.Natural (((s + 1) mod 9))) else (if s mod 3 = 1 then (Classes_Test.Number.Integer ((int ((s + 1) mod 9) - 4))) else (Classes_Test.Number.Real (((of_int (int ((s + 1) mod 9) - 4) / of_nat (((s + 1) mod 3)+1)) :: real)))))"

definition adapter_rat_of_real :: "real \<Rightarrow> rat" where
 "adapter_rat_of_real x = (SOME q. Real.Ratreal q = x)"
declare adapter_rat_of_real_def[code del]
lemma adapter_rat_of_real_code [code]: "adapter_rat_of_real (Real.Ratreal q) = q"
 unfolding adapter_rat_of_real_def by (rule some_equality) (simp_all add: Real.Ratreal_def)

fun encode_9267ab675f :: "Classes_Test.Number \<Rightarrow> nat list" where
 "encode_9267ab675f (Classes_Test.Number.Natural v0) = (List.Cons 0 (List.append (List.Cons (v0) List.Nil) List.Nil))" |
 "encode_9267ab675f (Classes_Test.Number.Integer v0) = (List.Cons 1 (List.append (List.Cons (if (v0) < 0 then nat (-2*(v0)-1) else nat (2*(v0))) List.Nil) List.Nil))" |
 "encode_9267ab675f (Classes_Test.Number.Real v0) = (List.Cons 2 (List.append (List.append (List.Cons (if ((fst ((Rat.quotient_of ((adapter_rat_of_real (v0))))))) < 0 then nat (-2*((fst ((Rat.quotient_of ((adapter_rat_of_real (v0)))))))-1) else nat (2*((fst ((Rat.quotient_of ((adapter_rat_of_real (v0))))))))) List.Nil) (List.Cons (if ((snd ((Rat.quotient_of ((adapter_rat_of_real (v0))))))) < 0 then nat (-2*((snd ((Rat.quotient_of ((adapter_rat_of_real (v0)))))))-1) else nat (2*((snd ((Rat.quotient_of ((adapter_rat_of_real (v0))))))))) List.Nil)) List.Nil))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Classes_Test.addnum :: (Classes_Test.Number \<Rightarrow> (Classes_Test.Number \<Rightarrow> Classes_Test.Number))) ((fixture_9267ab675f_2 ((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0)))) ((fixture_9267ab675f_2 ((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 1))))) in (encode_9267ab675f (result)))"
end
