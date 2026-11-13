theory Model imports WordChecked128_Test begin
declare Rust_Checked128_WordU128_Setup.rust_checked_word_power_def[symmetric, code_unfold del]
declare Rust_Checked128_Setup.rust_checked_integer_power_def[symmetric, code_unfold del]
declare Rust_Checked128_Setup.rust_checked_nat_power_def[symmetric, code_unfold del]

definition decode_int :: "nat \<Rightarrow> int" where
  "decode_int n = (if n mod 2 = 0 then int (n div 2) else - int (n div 2) - 1)"
definition encode_int :: "int \<Rightarrow> nat" where
  "encode_int z = (if 0 \<le> z then 2 * nat z else 2 * nat (-z) - 1)"
definition eb :: "bool \<Rightarrow> nat" where "eb b = (if b then 1 else 0)"


definition observe :: "nat list \<Rightarrow> nat list" where
"observe input = (let a = input!0; b = input!1; c = input!2; p = a mod 2 = 0; q = b mod 2 = 0; r = c mod 2 = 0; i = decode_int a; j = decode_int b; k = decode_int c; w = (of_nat a :: 64 word); v = (of_nat b :: 64 word) in (let d = Word_Setup_Common.word_bits w v (c mod 6) in [unat (fst d),unat (fst (snd d)),unat (fst (snd (snd d))),unat (fst (snd (snd (snd d)))),eb (snd (snd (snd (snd d))))]))"

end
