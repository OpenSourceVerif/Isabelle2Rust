theory Model imports Lists_Test begin

fun from_simple :: "nat list \<Rightarrow> nat Lists_Test.simple_list" where
 "from_simple [] = Lists_Test.SNil"
| "from_simple (x#xs) = Lists_Test.SCons x (from_simple xs)"
fun encode_simple :: "nat Lists_Test.simple_list \<Rightarrow> nat list" where
 "encode_simple Lists_Test.SNil = [0]"
| "encode_simple (Lists_Test.SCons x xs) = 1 # x # encode_simple xs"


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0; xs = from_simple (take (a mod 4) input) in encode_simple (Lists_Test.simple_cons_twice b xs))"

end
