theory Model imports Types_Test begin

primrec fixture :: "nat list \<Rightarrow> Types_Test.boolex" where
 "fixture [] = Types_Test.boolex.Const False" |
 "fixture (x#xs) = (if x mod 5 = 0 then Types_Test.boolex.Const (x mod 2 = 0)
 else if x mod 5 = 1 then Types_Test.boolex.Var x
 else if x mod 5 = 2 then Types_Test.boolex.Neg (fixture xs)
 else if x mod 5 = 3 then Types_Test.boolex.And (Types_Test.boolex.Var x) (fixture xs)
 else Types_Test.boolex.Or (Types_Test.boolex.Var x) (fixture xs))"

definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = [if Types_Test.eval (fixture input) (\<lambda>v. (v+hd(input@[0])) mod 2=0) then 1 else 0]"
end
