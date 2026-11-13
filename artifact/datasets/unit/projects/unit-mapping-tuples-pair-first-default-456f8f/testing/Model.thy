theory Model imports Tuples_Test begin


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0 in [Tuples_Test.pair_first_default (a,b)])"

end
