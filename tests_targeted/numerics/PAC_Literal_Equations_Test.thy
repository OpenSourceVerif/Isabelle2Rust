theory PAC_Literal_Equations_Test
  imports Rust_BigInt_Setup Rust_PAC_Character_Setup
begin

text \<open>
  PAC_Checker's unprimed literal decoder redirects to a primed constant that
  originally had only an SML printing. Both exported entry points must compute
  the ordered integer codes of all literal characters, including embedded
  zero. Rebuilding a literal from those codes must recover the original value.
\<close>

definition pac_decode :: "String.literal \<Rightarrow> integer list"
  where "pac_decode s = unsafe_asciis_of_literal s"

definition pac_decode_primed :: "String.literal \<Rightarrow> integer list"
  where "pac_decode_primed s = unsafe_asciis_of_literal' s"

definition pac_literal_roundtrip :: "String.literal \<Rightarrow> String.literal"
  where "pac_literal_roundtrip s = String.literal_of_asciis (unsafe_asciis_of_literal' s)"

lemma pac_literal_roundtrip_correct:
  "pac_literal_roundtrip s = s"
  by (simp add: pac_literal_roundtrip_def
      unsafe_asciis_of_literal'_def[symmetric] unsafe_asciis_of_literal_def)

export_code pac_decode pac_decode_primed pac_literal_roundtrip
  in Rust module_name PACLiteral

end
