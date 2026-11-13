theory Model imports Tuples_Test begin


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0 in (let v = Tuples_Test.pair_assoc ((a,b),c) in [fst v,fst (snd v),snd (snd v)]))"

end
