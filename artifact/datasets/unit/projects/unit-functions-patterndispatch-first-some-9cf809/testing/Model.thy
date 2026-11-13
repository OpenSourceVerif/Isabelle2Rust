theory Model imports PatternDispatch_Test begin


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0; t = (if c mod 3 = 0 then PatternDispatch_Test.Stop else if c mod 3 = 1 then PatternDispatch_Test.Push a else PatternDispatch_Test.Join (PatternDispatch_Test.Push a) (PatternDispatch_Test.Join PatternDispatch_Test.Stop (PatternDispatch_Test.Push b))); ps = (if c mod 2 = 0 then [] else [(a,b),(b,a)]) in [PatternDispatch_Test.first_some (Some a) b, PatternDispatch_Test.first_some None b])"

end
