theory Model imports Types_Test begin

primrec fixture :: "nat list \<Rightarrow> nat Types_Test.array" where
 "fixture [] = Types_Test.Null" | "fixture (x#xs) = Types_Test.Conn x (fixture xs)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [Types_Test.length (fixture input)]"
end
