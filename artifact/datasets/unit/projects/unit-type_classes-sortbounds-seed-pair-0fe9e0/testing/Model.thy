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
fun i2r_encode_1 :: "nat \<Rightarrow> nat list" where
"i2r_encode_1 x = [x]"

fun i2r_encode_0 :: "(nat \<times> nat) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_1 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (SortBounds_Test.seed_pair (input ! 0))"

end
