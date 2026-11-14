theory Model imports "source/2_functionalprog/Types_Test" begin
definition fixture_6d72026371_0 :: "nat \<Rightarrow> Types_Test.aexp" where
 "fixture_6d72026371_0 s = (Types_Test.aexp.Num (((s + 1) mod 9)))"

definition fixture_b738281f65_0 :: "nat \<Rightarrow> Types_Test.bexp" where
 "fixture_b738281f65_0 s = (Types_Test.bexp.Less ((fixture_6d72026371_0 (s + 1))) ((fixture_6d72026371_0 (s + 2))))"

definition fixture_6d72026371_1 :: "nat \<Rightarrow> Types_Test.aexp" where
 "fixture_6d72026371_1 s = (if s mod 4 = 0 then (Types_Test.aexp.IF ((fixture_b738281f65_0 (s + 1))) ((fixture_6d72026371_0 (s + 2))) ((fixture_6d72026371_0 (s + 3)))) else (if s mod 4 = 1 then (Types_Test.aexp.Add ((fixture_6d72026371_0 (s + 1))) ((fixture_6d72026371_0 (s + 2)))) else (if s mod 4 = 2 then (Types_Test.aexp.Sub ((fixture_6d72026371_0 (s + 1))) ((fixture_6d72026371_0 (s + 2)))) else (Types_Test.aexp.Num (((s + 1) mod 9))))))"

definition fixture_b738281f65_1 :: "nat \<Rightarrow> Types_Test.bexp" where
 "fixture_b738281f65_1 s = (if s mod 3 = 0 then (Types_Test.bexp.Less ((fixture_6d72026371_0 (s + 1))) ((fixture_6d72026371_0 (s + 2)))) else (if s mod 3 = 1 then (Types_Test.bexp.And ((fixture_b738281f65_0 (s + 1))) ((fixture_b738281f65_0 (s + 2)))) else (Types_Test.bexp.Neg ((fixture_b738281f65_0 (s + 1))))))"

definition fixture_b738281f65_2 :: "nat \<Rightarrow> Types_Test.bexp" where
 "fixture_b738281f65_2 s = (if s mod 3 = 0 then (Types_Test.bexp.Less ((fixture_6d72026371_1 (s + 1))) ((fixture_6d72026371_1 (s + 2)))) else (if s mod 3 = 1 then (Types_Test.bexp.And ((fixture_b738281f65_1 (s + 1))) ((fixture_b738281f65_1 (s + 2)))) else (Types_Test.bexp.Neg ((fixture_b738281f65_1 (s + 1))))))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Types_Test.evalb :: (Types_Test.bexp \<Rightarrow> bool)) ((fixture_b738281f65_2 ((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0))))) in (List.Cons (if (result) then 1 else 0) List.Nil))"
end
