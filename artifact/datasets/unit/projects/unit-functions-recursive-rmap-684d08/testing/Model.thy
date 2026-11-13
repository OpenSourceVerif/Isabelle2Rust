theory Model imports Recursive_Test begin

fun from_list :: "nat list \<Rightarrow> nat Recursive_Test.rlist" where
 "from_list [] = Recursive_Test.RNil"
| "from_list (x#xs) = Recursive_Test.RCons x (from_list xs)"
fun encode_list :: "nat Recursive_Test.rlist \<Rightarrow> nat list" where
 "encode_list Recursive_Test.RNil = [0]"
| "encode_list (Recursive_Test.RCons x xs) = 1 # x # encode_list xs"


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0; xs = from_list (take (a mod 4) input) in encode_list (Recursive_Test.rmap (\<lambda>x. x + 1) xs))"

end
