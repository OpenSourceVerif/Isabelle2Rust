theory Rust_BigInt_Int_Setup
  imports
    Rust_Setup
    "HOL-Library.Code_Target_Int"
begin

code_identifier
  code_module Int \<rightharpoonup> (Rust) Arith
| code_module Code_Target_Int \<rightharpoonup> (Rust) Arith

(* Code_Numeral.integer and HOL int via num-bigint. *)
code_printing
  type_constructor "integer" \<rightharpoonup>
    (Rust) "BigInt"
| type_constructor int \<rightharpoonup>
    (Rust) "BigInt"

code_printing
  constant "0 :: integer" \<rightharpoonup>
    (Rust) "BigInt::ZERO"
| constant int_of_integer \<rightharpoonup>
    (Rust) "_"
| constant integer_of_int \<rightharpoonup>
    (Rust) "_"

setup \<open>
Numeral.add_code \<^const_name>\<open>Code_Numeral.Pos\<close> I Code_Printer.literal_numeral "Rust"
#> Numeral.add_code \<^const_name>\<open>Code_Numeral.Neg\<close> (~) Code_Printer.literal_numeral "Rust"
\<close>

(** Keep these precedence levels aligned with Rust, not Isabelle surface syntax:
    multiplicative 10, additive 9, shifts 8, &, ^, | at 7, 6, 5, followed by
    comparisons 4 and boolean &&, || at 3, 2.  The serializer uses the levels
    to preserve the HOL expression tree with parentheses. **)
code_printing
  constant "plus :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 9 "+"
| constant "uminus :: integer \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!(- _)"
| constant "minus :: integer \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 9 "-"
| constant Code_Numeral.dup \<rightharpoonup>
    (Rust) "!(_ << 1usize)"
| constant Code_Numeral.sub \<rightharpoonup>
    (Rust) "panic'!(\"sub\")"
| constant "times :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 10 "*"
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
