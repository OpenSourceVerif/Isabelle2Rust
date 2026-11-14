theory Model imports "source/2_functionalprog/Function_Test" begin
fun encode_a70ca95382 :: "(unit Function_Test.info.info_ext) \<Rightarrow> nat list" where
 "encode_a70ca95382 (Function_Test.info.info_ext v0 v1 v2 v3) = (List.Cons 0 (List.append (List.Cons (List.length (v0)) (List.concat (List.map (\<lambda>v. (List.Cons ((of_char (v) :: nat)) List.Nil)) (v0)))) (List.append (List.Cons (List.length (v1)) (List.concat (List.map (\<lambda>v. (List.Cons ((of_char (v) :: nat)) List.Nil)) (v1)))) (List.append (List.Cons (if (v2) < 0 then nat (-2*(v2)-1) else nat (2*(v2))) List.Nil) (List.append (List.Cons (0) List.Nil) List.Nil)))))"

definition fixture_a70ca95382_2 :: "nat \<Rightarrow> (unit Function_Test.info.info_ext)" where
 "fixture_a70ca95382_2 s = (Function_Test.info.info_ext ((List.map (\<lambda>j. (List.nth ''abc '' (((s + 1)+j) mod 4))) [0..<((s + 1) mod 4)])) ((List.map (\<lambda>j. (List.nth ''abc '' (((s + 2)+j) mod 4))) [0..<((s + 2) mod 4)])) ((int ((s + 3) mod 9) - 4)) (()))"

fun encode_3bfe553bb3 :: "((unit Function_Test.info.info_ext) Function_Test.valT) \<Rightarrow> nat list" where
 "encode_3bfe553bb3 (Function_Test.valT.I v0) = (List.Cons 0 (List.append (List.Cons (if (v0) < 0 then nat (-2*(v0)-1) else nat (2*(v0))) List.Nil) List.Nil))" |
 "encode_3bfe553bb3 (Function_Test.valT.S v0) = (List.Cons 1 (List.append (List.Cons (List.length (v0)) (List.concat (List.map (\<lambda>v. (List.Cons ((of_char (v) :: nat)) List.Nil)) (v0)))) List.Nil))" |
 "encode_3bfe553bb3 (Function_Test.valT.L v0) = (List.Cons 2 (List.append (List.Cons (List.length (v0)) (List.concat (List.map (\<lambda>v. (encode_a70ca95382 (v))) (v0)))) List.Nil))" |
 "encode_3bfe553bb3 (Function_Test.valT.T v0) = (List.Cons 3 (List.append (List.Cons (List.length (List.map (\<lambda>i. (fixture_a70ca95382_2 (i))) [0..<9])) (List.concat (List.map (\<lambda>p. (List.Cons (if p \<in> (v0) then 1 else 0) List.Nil)) (List.map (\<lambda>i. (fixture_a70ca95382_2 (i))) [0..<9])))) List.Nil))"
definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let result = ((Function_Test.kvs1 :: (int \<Rightarrow> (((unit Function_Test.info.info_ext) Function_Test.valT) option))) ((int (((List.nth (List.append input (List.Cons (0) (List.Cons (1) (List.Cons (2) (List.Cons (3) (List.Cons (4) (List.Cons (5) (List.Cons (6) (List.Cons (7) List.Nil))))))))) 0)) mod 9) - 4))) in (case (result) of Option.None \<Rightarrow> (List.Cons (0) List.Nil) | Option.Some v \<Rightarrow> List.Cons 1 (encode_3bfe553bb3 (v))))"
end
