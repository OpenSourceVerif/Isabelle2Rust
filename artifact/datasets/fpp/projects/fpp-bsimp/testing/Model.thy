theory Model imports BExp_Test begin

definition dec :: "nat \<Rightarrow> int" where "dec n = (if n mod 2 = 1 then - int (Suc (n div 2)) else int (n div 2))"
definition enc :: "int \<Rightarrow> nat" where "enc z = (if z < 0 then 2 * nat (-z) - 1 else 2 * nat z)"
(* Exact wire conversion avoids an incomplete generic int Ord instance in the
   existing Rust serializer. Isabelle checks this observation-only equation. *)
declare enc_def[code del]
lemma enc_integer_wire [code]:
 "enc z = (if z < 0 then 2 * nat_of_integer (integer_of_int (-z)) - 1 else 2 * nat_of_integer (integer_of_int z))"
 by (simp add: enc_def nat_of_integer.rep_eq)


primrec expression :: "nat list \<Rightarrow> AExp_Test.aexp" where
 "expression [] = AExp_Test.N 0" |
 "expression (x#xs) = AExp_Test.Plus (if x mod 3 = 0 then AExp_Test.N (dec x) else if x mod 3 = 1 then AExp_Test.V ''x'' else AExp_Test.V ''y'') (expression xs)"
definition environment :: "nat list \<Rightarrow> AExp_Test.state" where
 "environment xs = (\<lambda>v. if v = ''x'' then dec (hd (xs@[0])) else if v = ''y'' then dec (length xs) else 0)"
fun encode_exp :: "AExp_Test.aexp \<Rightarrow> nat list" where
 "encode_exp (AExp_Test.N i) = [0,enc i]" |
 "encode_exp (AExp_Test.V v) = [1,if v = ''x'' then 0 else 1]" |
 "encode_exp (AExp_Test.Plus a b) = [2] @ encode_exp a @ encode_exp b"

definition expression_b :: "nat list \<Rightarrow> BExp_Test.bexp" where
 "expression_b xs = BExp_Test.And (BExp_Test.Not (BExp_Test.Bc (length xs mod 2 = 0))) (BExp_Test.Less (expression xs) (AExp_Test.V ''x''))"
fun encode_bexp :: "BExp_Test.bexp \<Rightarrow> nat list" where
 "encode_bexp (BExp_Test.Bc b) = [0,if b then 1 else 0]" |
 "encode_bexp (BExp_Test.Not b) = [1] @ encode_bexp b" |
 "encode_bexp (BExp_Test.And a b) = [2] @ encode_bexp a @ encode_bexp b" |
 "encode_bexp (BExp_Test.Less a b) = [3] @ encode_exp a @ encode_exp b"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = encode_bexp (BExp_Test.bsimp (expression_b input))"
end
