theory Rust_Setup
  imports "Main"
begin

ML_file \<open>code_rust.ML\<close>

code_identifier
  code_module Code_Target_Nat \<rightharpoonup> (Rust) Arith
| code_module Code_Target_Int \<rightharpoonup> (Rust) Arith
| code_module Code_Numeral \<rightharpoonup> (Rust) Arith

code_printing
  constant Code.abort \<rightharpoonup> (Rust) "panic!( _ )"

(* Bools *)
subsection \<open>bool and logic connectives\<close>
code_printing
  type_constructor bool \<rightharpoonup> (Rust) "bool"
| constant False \<rightharpoonup> (Rust) "false"
| constant True \<rightharpoonup> (Rust) "true"

code_reserved
  (Rust) bool

subsection \<open>String\<close>
(*infix ??>*)
code_printing
  type_constructor String.literal \<rightharpoonup> (Rust) "String"
(*| constant "STR ''''" \<rightharpoonup> (Rust) "\"\""*)
| constant "STR ''''" \<rightharpoonup> (Rust) "String::new()"
| constant "Groups.plus_class.plus :: String.literal \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infix 6 "((_).clone() + (_).as_str())"                             (*(Rust) infix 6 "+"*)
| constant "HOL.equal :: String.literal \<Rightarrow> String.literal \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "(_ == _)"
| constant "(\<le>) :: String.literal \<Rightarrow> String.literal \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "(_ <= _)"
| constant "(<) :: String.literal \<Rightarrow> String.literal \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "(_ < _)"

setup \<open>
  fold Literal.add_code ["Rust"]
\<close>

end