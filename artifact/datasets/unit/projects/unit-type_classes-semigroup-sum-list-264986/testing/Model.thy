theory Model imports Semigroup_Test begin
fun i2r_encode_0 :: "Nat \<Rightarrow> nat list" where
"i2r_encode_0 (Zero) = [0]"
| "i2r_encode_0 (Suc x0) = [1] @ i2r_encode_0 (x0)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Semigroup_Test.sum_list (if (input ! 0) mod 3 = 0 then [] else [((if (input ! 1) mod 2 = 0 then (Zero) else (Suc ((Zero) :: Nat))) :: Nat), ((if (input ! 3) mod 2 = 0 then (Zero) else (Suc ((Zero) :: Nat))) :: Nat)]))"

end
