theory Model imports ArithmeticChecked128_Test begin
declare Rust_Checked128_Setup.rust_checked_integer_power_def[symmetric, code_unfold del]
declare Rust_Checked128_Setup.rust_checked_nat_power_def[symmetric, code_unfold del]

definition decode_int :: "nat \<Rightarrow> int" where
  "decode_int n = (if n mod 2 = 0 then int (n div 2) else - int (n div 2) - 1)"
definition encode_int :: "int \<Rightarrow> nat" where
  "encode_int z = (if 0 \<le> z then 2 * nat z else 2 * nat (-z) - 1)"
definition ei :: "integer \<Rightarrow> nat" where "ei x = encode_int (int_of_integer x)"
definition eb :: "bool \<Rightarrow> nat" where "eb b = (if b then 1 else 0)"


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0; i = decode_int a; j = decode_int b; k = decode_int c; x = integer_of_int i; y = integer_of_int j; z = integer_of_int k in (let v = ArithmeticChecked128_Test.checked_int_div_mod x y in [ei (fst v),ei (snd v)]))"

end
