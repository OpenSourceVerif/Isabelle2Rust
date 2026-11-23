theory MFOTL_String_Equations_Test
  imports Rust_BigInt_Setup Rust_MFOTL_String_Setup
begin

text \<open>
  Event_Data removes the lifted string8 comparison and literal-input code
  equations for an OCaml-only adaptation. Export them through their original
  eight-bit list representation. Equality and lexicographic order must preserve
  all 256 character values, embedded zeroes, and proper-prefix ordering.
  Conversion from a seven-bit String.literal must preserve its complete list.
\<close>

definition mfotl_string8_eq :: "char list \<Rightarrow> char list \<Rightarrow> bool"
  where "mfotl_string8_eq xs ys = HOL.equal (Abs_string8 xs) (Abs_string8 ys)"

definition mfotl_string8_le :: "char list \<Rightarrow> char list \<Rightarrow> bool"
  where "mfotl_string8_le xs ys = (Abs_string8 xs \<le> Abs_string8 ys)"

definition mfotl_string8_lt :: "char list \<Rightarrow> char list \<Rightarrow> bool"
  where "mfotl_string8_lt xs ys = (Abs_string8 xs < Abs_string8 ys)"

definition mfotl_string8_from_literal :: "String.literal \<Rightarrow> string8"
  where "mfotl_string8_from_literal s = string8_literal s"

lemma mfotl_string8_literal_preserves_chars:
  "Rep_string8 (mfotl_string8_from_literal s) = String.explode s"
  by (simp add: mfotl_string8_from_literal_def
      string8_literal.rep_eq)

text \<open>
  Separate the comparison module from the literal converter so their executable
  obligations can be checked independently. The standard literal decoder also
  uses generic integer operations; a missing native numeric instance must not
  prevent the byte-comparison regression from being run.
\<close>

export_code mfotl_string8_eq mfotl_string8_le mfotl_string8_lt
  in Rust module_name MFOTLString

export_code mfotl_string8_from_literal in Rust module_name MFOTLLiteral

end
