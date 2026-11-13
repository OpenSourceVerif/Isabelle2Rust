theory Model imports MutChains_Test begin
fun i2r_encode_0 :: "peano \<Rightarrow> nat list" where
"i2r_encode_0 (Z) = [0]"
| "i2r_encode_0 (S x0) = [1] @ i2r_encode_0 (x0)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (MutChains_Test.grow ((if (input ! 0) mod 2 = 0 then (Z) else (S ((if (input ! 1) mod 2 = 0 then (Z) else (S ((Z) :: peano))) :: peano))) :: peano))"

end
