theory Model imports ContainerClasses_Test begin
fun i2r_encode_2 :: "bool \<Rightarrow> nat list" where
"i2r_encode_2 x = [if x then 1 else 0]"

fun i2r_encode_1 :: "(bool list) \<Rightarrow> nat list" where
"i2r_encode_1 [] = [0]"
| "i2r_encode_1 (x # xs) = 1 # (i2r_encode_2 (x) @ i2r_encode_1 xs)"

fun i2r_encode_0 :: "((bool list) list) \<Rightarrow> nat list" where
"i2r_encode_0 [] = [0]"
| "i2r_encode_0 (x # xs) = 1 # (i2r_encode_1 (x) @ i2r_encode_0 xs)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (ContainerClasses_Test.nested_list_flip (if (input ! 0) mod 3 = 0 then [] else [(if (input ! 1) mod 3 = 0 then [] else [((input ! 2) mod 2 = 0), ((input ! 3) mod 2 = 0)]), (if (input ! 4) mod 3 = 0 then [] else [((input ! 5) mod 2 = 0), ((input ! 6) mod 2 = 0)])]))"

end
