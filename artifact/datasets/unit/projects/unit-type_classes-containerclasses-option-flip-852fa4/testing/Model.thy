theory Model imports ContainerClasses_Test begin
fun i2r_encode_1 :: "bool \<Rightarrow> nat list" where
"i2r_encode_1 x = [if x then 1 else 0]"

fun i2r_encode_0 :: "(bool option) \<Rightarrow> nat list" where
"i2r_encode_0 None = [0]"
| "i2r_encode_0 (Some x) = 1 # i2r_encode_1 (x)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = i2r_encode_0 (ContainerClasses_Test.option_flip (if (input ! 0) mod 2 = 0 then None else Some ((input ! 1) mod 2 = 0)))"

end
