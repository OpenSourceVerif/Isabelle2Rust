theory Model imports Types_Test begin
primrec fixture :: "nat list \<Rightarrow> Types_Test.aexp" where
 "fixture [] = Types_Test.Num 0" |
 "fixture (x#xs) = (let t=fixture xs; n=Types_Test.Num x in
  if x mod 3 = 0 then Types_Test.Add n t
  else if x mod 3 = 1 then Types_Test.Sub n t
  else Types_Test.IF (Types_Test.Neg (Types_Test.Less n t)) t n)"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [Types_Test.evala (fixture input)]"
end
