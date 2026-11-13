theory Model imports ContainerClasses_Test begin
fun i2r_encode_1 :: "bool \<Rightarrow> nat list" where
"i2r_encode_1 x = [if x then 1 else 0]"

fun i2r_encode_2 :: "(bool list) \<Rightarrow> nat list" where
"i2r_encode_2 [] = [0]"
| "i2r_encode_2 (x # xs) = 1 # (i2r_encode_1 (x) @ i2r_encode_2 xs)"

fun i2r_encode_0 :: "(bool \<times> (bool list)) \<Rightarrow> nat list" where
"i2r_encode_0 (x,y) = i2r_encode_1 (x) @ i2r_encode_2 (y)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (ContainerClasses_Test.pair_flip (((input ! 1) mod 2 = 0), (if (input ! 2) mod 3 = 0 then [] else [((input ! 3) mod 2 = 0), ((input ! 4) mod 2 = 0)])))"

end
