theory Model imports BasicDefinitions_Test begin

definition decode_int :: "nat \<Rightarrow> int" where
  "decode_int n = (if n mod 2 = 0 then int (n div 2) else - int (n div 2) - 1)"
definition encode_int :: "int \<Rightarrow> nat" where
  "encode_int z = (if 0 \<le> z then 2 * nat z else 2 * nat (-z) - 1)"


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0; i = decode_int a; j = decode_int b; k = decode_int c in [encode_int (BasicDefinitions_Test.rust_keyword_arg i)])"

end
