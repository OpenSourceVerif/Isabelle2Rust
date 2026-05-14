theory Rust_Setup
  imports "Main"
begin

ML_file \<open>code_debug_info.ML\<close>
ML_file \<open>code_rust.ML\<close>



(** module remapping to prevent module dependency problem **)

code_identifier
  code_module Nat \<rightharpoonup> (Rust) Arith
| code_module Num \<rightharpoonup> (Rust) Arith
| code_module Groups \<rightharpoonup> (Rust) Arith
| code_module Power \<rightharpoonup> (Rust) Arith
| code_module Code_Numeral \<rightharpoonup> (Rust) Arith

code_printing
  constant Code.abort \<rightharpoonup> (Rust) "panic'!( _ )"


(* Bools *)
code_printing
  type_constructor bool \<rightharpoonup> 
    (Rust) "bool"
| constant False \<rightharpoonup> 
    (Rust) "false"
| constant True \<rightharpoonup> 
    (Rust) "true"

code_printing
  constant Not \<rightharpoonup>
    (Rust) "'! _"
| constant HOL.conj \<rightharpoonup>
    (Rust) infixl 3 "&&"
| constant HOL.disj \<rightharpoonup>
    (Rust) infixl 2 "||"


code_reserved
  (Rust) bool


(* Product Type *)
code_printing
  class_instance bool :: equal \<rightharpoonup>
    (Rust) -
| constant "HOL.equal :: bool \<Rightarrow> bool \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "=="

code_printing
  type_constructor unit \<rightharpoonup>
    (Rust) "()"
| constant Unity \<rightharpoonup>
    (Rust) "()"
| class_instance unit :: equal \<rightharpoonup>
    (Rust) -
| constant "HOL.equal :: unit \<Rightarrow> unit \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "=="

code_printing
  type_constructor prod \<rightharpoonup>
    (Rust) "!((_),/ (_))"
| constant Pair \<rightharpoonup>
    (Rust) "!((_),/ (_))"
| class_instance prod :: equal \<rightharpoonup>
    (Rust) -
| constant "HOL.equal :: 'a \<times> 'b \<Rightarrow> 'a \<times> 'b \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "=="


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
    (Rust) "!(match (_.clone(), _.clone()) { (k, l) => { let k = k.abs(); let l = l.abs(); if l == BigInt::ZERO { (BigInt::ZERO, k) } else { let q = k.clone() '/ l.clone(); let r = k % l; (q, r) } } })"
| constant "HOL.equal :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "=="
| constant "less_eq :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<="
| constant "less :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<"
| constant "abs :: integer \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!(_.abs())"
| constant "Bit_Operations.and :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 7 "&"
| constant "Bit_Operations.or :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 5 "|"
| constant "Bit_Operations.xor :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 6 "^"
| constant "Bit_Operations.not :: integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "'! _"
end