theory Model imports Semigroup_Test begin
fun i2r_encode_1 :: "Nat \<Rightarrow> nat list" where
"i2r_encode_1 (Zero) = [0]"
| "i2r_encode_1 (Suc x0) = [1] @ i2r_encode_1 (x0)"

fun i2r_encode_0 :: "((Nat, Nat) pair_box) \<Rightarrow> nat list" where
"i2r_encode_0 (PairBox x0 x1) = [0] @ i2r_encode_1 (x0) @ i2r_encode_1 (x1)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Semigroup_Test.sum_box ((PairBox ((if (input ! 1) mod 2 = 0 then (Zero) else (Suc ((Zero) :: Nat))) :: Nat) ((if (input ! 3) mod 2 = 0 then (Zero) else (Suc ((Zero) :: Nat))) :: Nat)) :: ((Nat, Nat) pair_box)))"

end
