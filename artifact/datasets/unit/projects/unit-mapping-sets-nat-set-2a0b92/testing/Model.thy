theory Model imports Sets_Test begin
definition eb :: "bool \<Rightarrow> nat" where "eb b = (if b then 1 else 0)"


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0 in [eb (a \<in> Sets_Test.nat_set),card Sets_Test.nat_set])"

end
