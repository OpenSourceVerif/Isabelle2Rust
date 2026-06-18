theory Rust_BigInt_Nat_Setup
  imports
    Rust_BigInt_Int_Setup
    "HOL-Library.Code_Target_Nat"
begin

code_identifier
  code_module Code_Target_Nat \<rightharpoonup> (Rust) Arith

code_printing
  type_constructor nat \<rightharpoonup>
    (Rust) "BigInt"
| constant Code_Target_Nat.Nat \<rightharpoonup>
    (Rust) "_"
| constant Code_Numeral.nat_of_integer \<rightharpoonup>
    (Rust) "!(match _.clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })"
| constant integer_of_nat \<rightharpoonup>
    (Rust) "_"
| constant "0 :: nat" \<rightharpoonup>
    (Rust) "BigInt::ZERO"
| constant "plus :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 6 "+"
| constant "minus :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!(match (_.clone(), _.clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })"
| constant "times :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 7 "*"
| constant "HOL.equal :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "=="
| constant "less_eq :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<="
| constant "less :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<"

end
