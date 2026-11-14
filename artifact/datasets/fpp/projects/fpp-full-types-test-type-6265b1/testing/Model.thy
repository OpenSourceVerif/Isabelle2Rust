theory Model imports "source/2_functionalprog/Types_Test" begin
definition fixture_1c0d3ce76e_2 :: "nat \<Rightarrow> Types_Test.Exp" where
 "fixture_1c0d3ce76e_2 s = (if s mod 3 = 0 then (Types_Test.Exp.B (((s + 1) mod 2 = 0))) else (if s mod 3 = 1 then (Types_Test.Exp.I ((int ((s + 1) mod 9) - 4))) else (Types_Test.Exp.N (((s + 1) mod 9)))))"

fun encode_4976f5008f :: "Types_Test.Type \<Rightarrow> nat list" where
 "encode_4976f5008f (Types_Test.Type.Bool ) = (List.Cons 0 List.Nil)" |
 "encode_4976f5008f (Types_Test.Type.Integer ) = (List.Cons 1 List.Nil)" |
 "encode_4976f5008f (Types_Test.Type.Nature ) = (List.Cons 2 List.Nil)"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Types_Test.type :: (Types_Test.Exp \<Rightarrow> Types_Test.Type)) ((fixture_1c0d3ce76e_2 ((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0))))) in (encode_4976f5008f (result)))"
end
