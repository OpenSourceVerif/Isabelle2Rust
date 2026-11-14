theory Model imports "source/5_IMP/BExp_Test" begin
definition fixture_cdfc980b60_0 :: "nat \<Rightarrow> AExp_Test.aexp" where
 "fixture_cdfc980b60_0 s = (AExp_Test.aexp.N ((int ((s + 1) mod 9) - 4)))"

definition fixture_cdfc980b60_1 :: "nat \<Rightarrow> AExp_Test.aexp" where
 "fixture_cdfc980b60_1 s = (if s mod 3 = 0 then (AExp_Test.aexp.N ((int ((s + 1) mod 9) - 4))) else (if s mod 3 = 1 then (AExp_Test.aexp.V ((List.map (\<lambda>j. (List.nth ''abc '' (((s + 1)+j) mod 4))) [0..<((s + 1) mod 4)]))) else (AExp_Test.aexp.Plus ((fixture_cdfc980b60_0 (s + 1))) ((fixture_cdfc980b60_0 (s + 2))))))"

definition fixture_cdfc980b60_2 :: "nat \<Rightarrow> AExp_Test.aexp" where
 "fixture_cdfc980b60_2 s = (if s mod 3 = 0 then (AExp_Test.aexp.N ((int ((s + 1) mod 9) - 4))) else (if s mod 3 = 1 then (AExp_Test.aexp.V ((List.map (\<lambda>j. (List.nth ''abc '' (((s + 1)+j) mod 4))) [0..<((s + 1) mod 4)]))) else (AExp_Test.aexp.Plus ((fixture_cdfc980b60_1 (s + 1))) ((fixture_cdfc980b60_1 (s + 2))))))"

fun encode_cdfc980b60 :: "AExp_Test.aexp \<Rightarrow> nat list" where
 "encode_cdfc980b60 (AExp_Test.aexp.N v0) = (List.Cons 0 (List.append (List.Cons (if (v0) < 0 then nat (-2*(v0)-1) else nat (2*(v0))) List.Nil) List.Nil))" |
 "encode_cdfc980b60 (AExp_Test.aexp.V v0) = (List.Cons 1 (List.append (List.Cons (List.length (v0)) (List.concat (List.map (\<lambda>v. (List.Cons ((of_char (v) :: nat)) List.Nil)) (v0)))) List.Nil))" |
 "encode_cdfc980b60 (AExp_Test.aexp.Plus v0 v1) = (List.Cons 2 (List.append (encode_cdfc980b60 (v0)) (List.append (encode_cdfc980b60 (v1)) List.Nil)))"

fun encode_66c20751db :: "BExp_Test.bexp \<Rightarrow> nat list" where
 "encode_66c20751db (BExp_Test.bexp.Bc v0) = (List.Cons 0 (List.append (List.Cons (if (v0) then 1 else 0) List.Nil) List.Nil))" |
 "encode_66c20751db (BExp_Test.bexp.Not v0) = (List.Cons 1 (List.append (encode_66c20751db (v0)) List.Nil))" |
 "encode_66c20751db (BExp_Test.bexp.And v0 v1) = (List.Cons 2 (List.append (encode_66c20751db (v0)) (List.append (encode_66c20751db (v1)) List.Nil)))" |
 "encode_66c20751db (BExp_Test.bexp.Less v0 v1) = (List.Cons 3 (List.append (encode_cdfc980b60 (v0)) (List.append (encode_cdfc980b60 (v1)) List.Nil)))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((BExp_Test.less :: (AExp_Test.aexp \<Rightarrow> (AExp_Test.aexp \<Rightarrow> BExp_Test.bexp))) ((fixture_cdfc980b60_2 ((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0)))) ((fixture_cdfc980b60_2 ((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 1))))) in (encode_66c20751db (result)))"
end
