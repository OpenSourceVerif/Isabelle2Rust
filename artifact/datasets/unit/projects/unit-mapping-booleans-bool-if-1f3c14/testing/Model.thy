theory Model imports Booleans_Test begin

definition encode_bool :: "bool \<Rightarrow> nat" where
  "encode_bool b = (if b then 1 else 0)"


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0 in [encode_bool (Booleans_Test.bool_if p q r)])"

end
