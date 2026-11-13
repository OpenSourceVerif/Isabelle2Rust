theory Model imports SortBounds_Test begin
instantiation nat :: seed
begin
definition seed_nat where "seed = (0::nat)"
instance ..
end
instantiation nat :: tick
begin
definition tick_nat where "tick (x::nat) = x + 1"
instance ..
end
fun i2r_encode_0 :: "nat \<Rightarrow> nat list" where
"i2r_encode_0 x = [x]"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (SortBounds_Test.step_or_seed ((input ! 0) mod 2 = 0) (input ! 1))"

end
