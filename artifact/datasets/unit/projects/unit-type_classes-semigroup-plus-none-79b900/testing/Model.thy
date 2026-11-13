theory Model imports Semigroup_Test begin
fun i2r_encode_1 :: "Nat \<Rightarrow> nat list" where
"i2r_encode_1 (Zero) = [0]"
| "i2r_encode_1 (Suc x0) = [1] @ i2r_encode_1 (x0)"

fun i2r_encode_0 :: "(Nat option) \<Rightarrow> nat list" where
"i2r_encode_0 None = [0]"
| "i2r_encode_0 (Some x) = 1 # i2r_encode_1 (x)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (Semigroup_Test.plus_none (if (input ! 0) mod 2 = 0 then None else Some ((if (input ! 1) mod 2 = 0 then (Zero) else (Suc ((Zero) :: Nat))) :: Nat)))"

end
