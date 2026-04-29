theory Rust_Setup
  imports "Main"
begin

ML_file \<open>code_debug_info.ML\<close>
ML_file \<open>code_rust.ML\<close>


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

(* Integers via num-bigint *)

code_printing
  type_constructor "integer" \<rightharpoonup> 
    (Rust) "BigInt"

code_printing
  constant "0 :: integer" \<rightharpoonup> 
    (Rust) "BigInt::ZERO"

setup \<open>
Numeral.add_code \<^const_name>\<open>Code_Numeral.Pos\<close> I Code_Printer.literal_numeral "Rust"
#> Numeral.add_code \<^const_name>\<open>Code_Numeral.Neg\<close> (~) Code_Printer.literal_numeral "Rust"
\<close>

code_printing
  constant "plus :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 6 "+"
| constant "uminus :: integer \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!(- _)"
| constant "minus :: integer \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 6 "-"
| constant Code_Numeral.dup \<rightharpoonup>
    (Rust) "!(_ << 1usize)"
| constant Code_Numeral.sub \<rightharpoonup>
    (Rust) "panic'!(\"sub\")"
| constant "times :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 7 "*"
| constant Code_Numeral.divmod_abs \<rightharpoonup>
    (Rust) "!(match (_, _) { (k, l) => { let k = if k < BigInt::ZERO { -k } else { k }; let l = if l < BigInt::ZERO { -l } else { l }; if l == BigInt::ZERO { (BigInt::ZERO, k) } else { let q = &k / &l; let r = k % l; (q, r) } } })"
| constant "HOL.equal :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "=="
| constant "less_eq :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<="
| constant "less :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<"
| constant "abs :: integer \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!(match _ { k => if k < BigInt::ZERO { -k } else { k } })"
| constant "Bit_Operations.and :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 7 "&"
| constant "Bit_Operations.or :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 5 "|"
| constant "Bit_Operations.xor :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 6 "^"
| constant "Bit_Operations.not :: integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "'! _"
end