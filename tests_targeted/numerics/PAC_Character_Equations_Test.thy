theory PAC_Character_Equations_Test
  imports Rust_BigInt_Setup Rust_PAC_Character_Setup
begin

text \<open>
  PAC_Checker rewrites character-to-word conversions to uint32_of_char, whose
  original setup provides only an SML printing. Export the word result itself,
  observe it as an integer, and exercise its actual string-hashing caller.
  Runtime checks cover all 256 HOL characters and literal hashes with wrapping
  32-bit arithmetic, including embedded zero and the maximum ASCII character.
\<close>

definition pac_char_word :: "char \<Rightarrow> uint32"
  where "pac_char_word c = uint32_of_char c"

definition pac_char_value :: "char \<Rightarrow> integer"
  where "pac_char_value c = integer_of_uint32 (uint32_of_char c)"

definition pac_hash_value :: "String.literal \<Rightarrow> integer"
  where "pac_hash_value s = integer_of_uint32 (hashcode_literal' s)"

export_code pac_char_word pac_char_value pac_hash_value
  in Rust module_name PACCharacter

end
