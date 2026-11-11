theory Model imports Types_Test begin
primrec fixture :: "nat list \<Rightarrow> nat Types_Test.array" where
 "fixture [] = Types_Test.Null" | "fixture (x#xs) = Types_Test.Conn x (fixture xs)"
primrec encode_array :: "nat Types_Test.array \<Rightarrow> nat list" where
 "encode_array Types_Test.Null = []" | "encode_array (Types_Test.Conn x xs) = x # encode_array xs"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let xs=input@[0]; i=hd(input@[0]) mod List.length xs in [Types_Test.nth (fixture xs) i])"
end
