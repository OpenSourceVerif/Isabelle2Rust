theory Rust_PAC_Character_Setup
  imports "PAC_Checker.PAC_Checker_Synthesis"
begin

text \<open>
  Optional adapter for the character conversion used by PAC_Checker's literal
  hash. Import it alongside the selected Rust numeric profile and declare the
  PAC_Checker session dependency.

  The source code_unfold rule combines uint32_of_int (int_of_char c) into
  uint32_of_char c. Supply an equation through the existing integer conversion
  and Uint32 constructor, so that this rule remains enabled without rewriting
  the right-hand side back to the same constant. Both conversions preserve all
  eight bits of HOL char, including values above the ASCII range. Uint32 keeps
  its existing modulo-2^32 semantics and representation.
\<close>

lemma rust_pac_uint32_of_char_code [code]:
  "uint32_of_char c = Uint32 (integer_of_char c)"
  by (simp add: uint32_of_char_def[symmetric] uint32_of_int_code
      int_of_char_def integer_of_char_def of_int_of_char)

end
