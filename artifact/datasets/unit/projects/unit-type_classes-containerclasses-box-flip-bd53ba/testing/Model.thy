theory Model imports ContainerClasses_Test begin
fun i2r_encode_2 :: "bool \<Rightarrow> nat list" where
"i2r_encode_2 x = [if x then 1 else 0]"

fun i2r_encode_1 :: "(bool list) \<Rightarrow> nat list" where
"i2r_encode_1 [] = [0]"
| "i2r_encode_1 (x # xs) = 1 # (i2r_encode_2 (x) @ i2r_encode_1 xs)"

fun i2r_encode_0 :: "((bool list) class_box) \<Rightarrow> nat list" where
"i2r_encode_0 (ClassBox x0) = [0] @ i2r_encode_1 (x0)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (ContainerClasses_Test.box_flip ((ClassBox (if (input ! 1) mod 3 = 0 then [] else [((input ! 2) mod 2 = 0), ((input ! 3) mod 2 = 0)])) :: ((bool list) class_box)))"

end
