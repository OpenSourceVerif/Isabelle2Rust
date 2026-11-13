theory Model imports InfixPrecedence_Test begin

definition decode_int :: "nat \<Rightarrow> int" where
  "decode_int n = (if n mod 2 = 0 then int (n div 2) else - int (n div 2) - 1)"
definition encode_int :: "int \<Rightarrow> nat" where
  "encode_int z = (if 0 \<le> z then 2 * nat z else 2 * nat (-z) - 1)"
definition ei :: "integer \<Rightarrow> nat" where "ei x = encode_int (int_of_integer x)"

fun encode_expr :: "InfixPrecedence_Test.iexpr \<Rightarrow> nat list" where
 "encode_expr (InfixPrecedence_Test.Lit x) = [0,ei x]"
| "encode_expr (InfixPrecedence_Test.Add l r) = [1] @ encode_expr l @ encode_expr r"


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0; i = decode_int a; j = decode_int b; k = decode_int c; x = integer_of_int i; y = integer_of_int j; z = integer_of_int k in encode_expr (InfixPrecedence_Test.build x y z (integer_of_int (decode_int (input!3)))))"

end
