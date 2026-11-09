theory Rust_MFOTL_String_Setup
  imports "MFOTL_Checker.Event_Data"
begin

text \<open>
  Optional equations for MFOTL_Checker's eight-bit string wrapper. Import this
  theory alongside the selected Rust profile and declare the MFOTL_Checker
  session dependency. Event_Data drops these equations for its OCaml native
  string adaptation. Restore the already proved lifted equations over the
  existing Abs_string8 constructor, retaining every bit of each HOL char and
  the source lexicographic order.

  Conversion from String.literal is total because its seven-bit characters
  are also valid eight-bit characters. The reverse literal_string8 operation
  uses String.Abs_literal on unrestricted input; it is deliberately not given
  an equation that silently truncates high bits or changes that abstraction.
\<close>

declare equal_string8.abs_eq [code]
declare less_eq_string8.abs_eq [code]
declare less_string8.abs_eq [code]
declare string8_literal.abs_eq [code]

end
