theory High_Level_Mapping_Test
  imports
    Main
    "HOL-Library.Code_Target_Int"
    "HOL-Library.Code_Target_Nat"
    "Rust.Rust_Setup"
begin

code_identifier
  code_module Int \<rightharpoonup> (Rust) Arith
| code_module Code_Target_Int \<rightharpoonup> (Rust) Arith
| code_module Code_Target_Nat \<rightharpoonup> (Rust) Arith

code_printing
  type_constructor int \<rightharpoonup>
    (Rust) "BigInt"
| constant int_of_integer \<rightharpoonup>
    (Rust) "_"
| constant integer_of_int \<rightharpoonup>
    (Rust) "_"

code_printing
  type_constructor nat \<rightharpoonup>
    (Rust) "BigInt"
| constant Code_Target_Nat.Nat \<rightharpoonup>
    (Rust) "_"
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

definition nat_branch :: "nat \<Rightarrow> nat \<Rightarrow> nat \<Rightarrow> nat" where
  "nat_branch x y z = (if x < y then x + z else y + z)"

definition nat_delta :: "nat \<Rightarrow> nat \<Rightarrow> nat" where
  "nat_delta x y = (if x < y then y - x else x - y)"

definition int_affine :: "int \<Rightarrow> int \<Rightarrow> int" where
  "int_affine x y = 3 * x - y + 7"

definition int_branch :: "int \<Rightarrow> int \<Rightarrow> int" where
  "int_branch x y = (if x < y then y - x else x - y)"

definition integer_affine :: "integer \<Rightarrow> integer \<Rightarrow> integer" where
  "integer_affine x y = 3 * x - y + 7"

definition integer_branch :: "integer \<Rightarrow> integer \<Rightarrow> integer" where
  "integer_branch x y = (if x < y then y - x else x - y)"

export_code
  nat_branch
  nat_delta
  int_affine
  int_branch
  integer_affine
  integer_branch
  in Rust

end
