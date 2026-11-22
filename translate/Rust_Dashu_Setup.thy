theory Rust_Dashu_Setup
  imports Rust_Base_Setup "HOL-Library.Code_Target_Int" "HOL-Library.Code_Target_Nat"
begin

text \<open>Arbitrary precision: nat uses dashu-int 0.6.2 UBig;
int and integer use IBig. Natural subtraction saturates, division is totalized,
and signed division rounds down with remainder having the divisor's sign.\<close>

code_identifier
  code_module Int \<rightharpoonup> (Rust) Arith
| code_module Code_Target_Int \<rightharpoonup> (Rust) Arith
| code_module Code_Target_Nat \<rightharpoonup> (Rust) Arith

code_printing code_module Rust_Dashu \<rightharpoonup> (Rust) \<open>
use dashu_int::{IBig, UBig};
pub fn from_int(n: IBig) -> UBig {
    if n <= IBig::ZERO { UBig::ZERO } else { n.into_parts().1 }
}
pub fn into_int(n: UBig) -> IBig { IBig::from(n) }
pub fn sub_nat(a: UBig, b: UBig) -> UBig {
    if a <= b { UBig::ZERO } else { a - b }
}
pub fn div_nat(a: UBig, b: UBig) -> UBig {
    if b == UBig::ZERO { UBig::ZERO } else { a / b }
}
pub fn rem_nat(a: UBig, b: UBig) -> UBig {
    if b == UBig::ZERO { a } else { a % b }
}
pub fn div_mod_floor(a: IBig, b: IBig) -> (IBig, IBig) {
    if b == IBig::ZERO { return (IBig::ZERO, a); }
    let mut q = &a / &b;
    let mut r = &a % &b;
    if r != IBig::ZERO && (r < IBig::ZERO) != (b < IBig::ZERO) {
        q -= IBig::ONE;
        r += b;
    }
    (q, r)
}
pub fn div_int(a: IBig, b: IBig) -> IBig { div_mod_floor(a,b).0 }
pub fn rem_int(a: IBig, b: IBig) -> IBig { div_mod_floor(a,b).1 }
pub fn abs_int(a: IBig) -> IBig { IBig::from(a.into_parts().1) }
pub fn divmod_abs(a: IBig, b: IBig) -> (IBig, IBig) {
    let a=a.into_parts().1; let b=b.into_parts().1;
    if b == UBig::ZERO { (IBig::ZERO, IBig::from(a)) }
    else { (IBig::from(&a / &b), IBig::from(a % b)) }
}
\<close>
code_reserved (Rust) Rust_Dashu

code_printing
  type_constructor integer \<rightharpoonup> (Rust) "dashu'_int::IBig"
| type_constructor int \<rightharpoonup> (Rust) "dashu'_int::IBig"
| type_constructor nat \<rightharpoonup> (Rust) "dashu'_int::UBig"

code_printing
  constant int_of_integer \<rightharpoonup> (Rust) "_"
| constant integer_of_int \<rightharpoonup> (Rust) "_"
| constant Code_Target_Nat.Nat \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::from'_int'(_')"
| constant Code_Numeral.nat_of_integer \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::from'_int'(_')"
| constant integer_of_nat \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::into'_int'(_')"

setup \<open>
let
  fun print_dashu_int _ k =
    "dashu_int::IBig::from_str_radix(\"" ^ (if k < 0 then "-" ^ Int.toString (~k) else Int.toString k) ^ "\", 10).unwrap()"
in
  Numeral.add_code \<^const_name>\<open>Code_Numeral.Pos\<close> I print_dashu_int "Rust"
  #> Numeral.add_code \<^const_name>\<open>Code_Numeral.Neg\<close> (~) print_dashu_int "Rust"
end
\<close>

code_printing
  constant "0 :: integer" \<rightharpoonup> (Rust) "dashu'_int::IBig::ZERO"
| constant "1 :: integer" \<rightharpoonup> (Rust) "dashu'_int::IBig::ONE"
| constant "plus :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 9 "+"
| constant "times :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 10 "*"
| constant "HOL.equal :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 4 "=="
| constant "less_eq :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 4 "<="
| constant "less :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 4 "<"
| constant "minus :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 9 "-"
| constant "divide :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::div'_int'(_, _')"
| constant "modulo :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::rem'_int'(_, _')"
| constant "uminus :: integer \<Rightarrow> _" \<rightharpoonup> (Rust) "!(- _)"
| constant "abs :: integer \<Rightarrow> _" \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::abs'_int'(_')"
| constant "0 :: int" \<rightharpoonup> (Rust) "dashu'_int::IBig::ZERO"
| constant "1 :: int" \<rightharpoonup> (Rust) "dashu'_int::IBig::ONE"
| constant "plus :: int \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 9 "+"
| constant "times :: int \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 10 "*"
| constant "HOL.equal :: int \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 4 "=="
| constant "less_eq :: int \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 4 "<="
| constant "less :: int \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 4 "<"
| constant "minus :: int \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 9 "-"
| constant "divide :: int \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::div'_int'(_, _')"
| constant "modulo :: int \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::rem'_int'(_, _')"
| constant "uminus :: int \<Rightarrow> _" \<rightharpoonup> (Rust) "!(- _)"
| constant "abs :: int \<Rightarrow> _" \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::abs'_int'(_')"
| constant "0 :: nat" \<rightharpoonup> (Rust) "dashu'_int::UBig::ZERO"
| constant "1 :: nat" \<rightharpoonup> (Rust) "dashu'_int::UBig::ONE"
| constant "plus :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 9 "+"
| constant "times :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 10 "*"
| constant "HOL.equal :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 4 "=="
| constant "less_eq :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 4 "<="
| constant "less :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 4 "<"
| constant "minus :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::sub'_nat'(_, _')"
| constant "divide :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::div'_nat'(_, _')"
| constant "modulo :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::rem'_nat'(_, _')"
| constant Code_Numeral.dup \<rightharpoonup> (Rust) "!(_ << 1usize)"
| constant Code_Numeral.divmod_abs \<rightharpoonup> (Rust) "!crate::Rust'_Dashu::divmod'_abs'(_, _')"
| constant "Bit_Operations.and :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup> (Rust) infixl 7 "&"
| constant "Bit_Operations.or :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup> (Rust) infixl 5 "|"
| constant "Bit_Operations.xor :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup> (Rust) infixl 6 "^"
| constant "Bit_Operations.not :: integer \<Rightarrow> integer" \<rightharpoonup> (Rust) "'! _"

end
