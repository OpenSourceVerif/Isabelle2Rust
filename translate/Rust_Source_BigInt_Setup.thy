theory Rust_Source_BigInt_Setup
  imports
    Rust_Base_Setup
    "HOL-Library.Code_Target_Int"
    "HOL-Library.Code_Target_Nat"
begin

text \<open>
  Optional arbitrary-precision profile with one Rust newtype per HOL source
  type: nat, int and integer. Distinct receiver types preserve type-class
  instance identity, including truncated natural and signed subtraction.
  Rust_BigInt_Setup remains the separate direct-BigInt profile.
\<close>

code_identifier
  code_module Int \<rightharpoonup> (Rust) Arith
| code_module Code_Target_Int \<rightharpoonup> (Rust) Arith
| code_module Code_Target_Nat \<rightharpoonup> (Rust) Arith

code_printing code_module Rust_Source_BigInt \<rightharpoonup> (Rust) \<open>
use num_bigint::BigInt;
use num_traits::Signed as _;

// Fields stay private so external clients cannot violate Nat's invariant.
macro_rules! wrapper {
    ($name:ident, $payload:ty, $normalize:expr) => {
        #[repr(transparent)]
        #[derive(Clone, Debug, PartialEq, Eq, PartialOrd, Ord)]
        pub struct $name(pub(crate) $payload);
        impl $name {
            pub const ZERO: Self = Self(<$payload>::ZERO);
            pub fn from_bigint(value: BigInt) -> Self { Self(($normalize)(value)) }
            pub fn into_bigint(self) -> BigInt { self.0.into() }
        }
        impl std::ops::Add for $name {
            type Output = Self;
            fn add(self, rhs: Self) -> Self { Self(self.0 + rhs.0) }
        }
        impl std::ops::Mul for $name {
            type Output = Self;
            fn mul(self, rhs: Self) -> Self { Self(self.0 * rhs.0) }
        }
    };
}
wrapper!(Nat, BigInt, |x: BigInt| if x < BigInt::ZERO { BigInt::ZERO } else { x });
wrapper!(Integer, BigInt, |x: BigInt| x);
// Code_Target_Int declares int_of_integer as a code constructor, also used
// in patterns (e.g. gcd/lcm). Preserve that boundary as a transparent newtype.
// Int -> Integer -> BigInt introduces no extra allocation.
wrapper!(Int, Integer, |x: BigInt| Integer::from_bigint(x));
impl From<Integer> for BigInt {
    fn from(value: Integer) -> BigInt { value.0 }
}

impl std::ops::Sub for Nat {
    type Output = Self;
    fn sub(self, rhs: Self) -> Self {
        if self.0 <= rhs.0 { Self::ZERO } else { Self(self.0 - rhs.0) }
    }
}
macro_rules! signed_operations {
    ($name:ident) => {
        impl std::ops::Sub for $name {
            type Output = Self;
            fn sub(self, rhs: Self) -> Self { Self(self.0 - rhs.0) }
        }
        impl std::ops::Neg for $name {
            type Output = Self;
            fn neg(self) -> Self { Self(-self.0) }
        }
        impl std::ops::BitAnd for $name {
            type Output = Self;
            fn bitand(self, rhs: Self) -> Self { Self(self.0 & rhs.0) }
        }
        impl std::ops::BitOr for $name {
            type Output = Self;
            fn bitor(self, rhs: Self) -> Self { Self(self.0 | rhs.0) }
        }
        impl std::ops::BitXor for $name {
            type Output = Self;
            fn bitxor(self, rhs: Self) -> Self { Self(self.0 ^ rhs.0) }
        }
        impl std::ops::Not for $name {
            type Output = Self;
            fn not(self) -> Self { Self(!self.0) }
        }
    };
}
signed_operations!(Int);
signed_operations!(Integer);

pub fn integer_of_int(Int(value): Int) -> Integer { value }
pub fn nat_of_integer(Integer(value): Integer) -> Nat { Nat::from_bigint(value) }
pub fn integer_of_nat(Nat(value): Nat) -> Integer { Integer(value) }
pub fn duplicate(Integer(value): Integer) -> Integer { Integer(value << 1usize) }
pub fn abs_integer(Integer(value): Integer) -> Integer { Integer(value.abs()) }
pub fn divmod_abs(Integer(lhs): Integer, Integer(rhs): Integer) -> (Integer, Integer) {
    let a = lhs.abs();
    let b = rhs.abs();
    if b == BigInt::ZERO {
        (Integer::ZERO, Integer(a))
    } else {
        (Integer(&a / &b), Integer(a % b))
    }
}
\<close>

code_reserved (Rust) Rust_Source_BigInt

code_printing
  type_constructor nat \<rightharpoonup> (Rust) "crate::Rust'_Source'_BigInt::Nat"
| type_constructor int \<rightharpoonup> (Rust) "crate::Rust'_Source'_BigInt::Int"
| type_constructor integer \<rightharpoonup> (Rust) "crate::Rust'_Source'_BigInt::Integer"

code_printing
  constant "0 :: integer" \<rightharpoonup> (Rust) "crate::Rust'_Source'_BigInt::Integer::ZERO"
| constant "0 :: nat" \<rightharpoonup> (Rust) "crate::Rust'_Source'_BigInt::Nat::ZERO"
| constant int_of_integer \<rightharpoonup> (Rust) "!crate::Rust'_Source'_BigInt::Int'(_')"
| constant integer_of_int \<rightharpoonup> (Rust) "!crate::Rust'_Source'_BigInt::integer'_of'_int'(_')"
| constant Code_Target_Nat.Nat \<rightharpoonup> (Rust) "!crate::Rust'_Source'_BigInt::nat'_of'_integer'(_')"
| constant Code_Numeral.nat_of_integer \<rightharpoonup> (Rust) "!crate::Rust'_Source'_BigInt::nat'_of'_integer'(_')"
| constant integer_of_nat \<rightharpoonup> (Rust) "!crate::Rust'_Source'_BigInt::integer'_of'_nat'(_')"

setup \<open>
let
  fun print_source_integer literals k =
    "crate::Rust_Source_BigInt::Integer::from_bigint(" ^
      Code_Printer.literal_numeral literals k ^ ")"
in
  Numeral.add_code \<^const_name>\<open>Code_Numeral.Pos\<close> I print_source_integer "Rust"
  #> Numeral.add_code \<^const_name>\<open>Code_Numeral.Neg\<close> (~) print_source_integer "Rust"
end
\<close>

code_printing
  constant "plus :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 9 "+"
| constant "minus :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 9 "-"
| constant "times :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 10 "*"
| constant "uminus :: integer \<Rightarrow> _" \<rightharpoonup> (Rust) "!(- _)"
| constant "HOL.equal :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup> (Rust) infix 4 "=="
| constant "less_eq :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup> (Rust) infix 4 "<="
| constant "less :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup> (Rust) infix 4 "<"
| constant "plus :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 9 "+"
| constant "minus :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 9 "-"
| constant "times :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup> (Rust) infixl 10 "*"
| constant "HOL.equal :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup> (Rust) infix 4 "=="
| constant "less_eq :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup> (Rust) infix 4 "<="
| constant "less :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup> (Rust) infix 4 "<"
| constant Code_Numeral.dup \<rightharpoonup> (Rust) "!crate::Rust'_Source'_BigInt::duplicate'(_')"
| constant Code_Numeral.divmod_abs \<rightharpoonup> (Rust) "!crate::Rust'_Source'_BigInt::divmod'_abs'(_, _')"
| constant "abs :: integer \<Rightarrow> _" \<rightharpoonup> (Rust) "!crate::Rust'_Source'_BigInt::abs'_integer'(_')"
| constant "Bit_Operations.and :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup> (Rust) infixl 7 "&"
| constant "Bit_Operations.or :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup> (Rust) infixl 5 "|"
| constant "Bit_Operations.xor :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup> (Rust) infixl 6 "^"
| constant "Bit_Operations.not :: integer \<Rightarrow> integer" \<rightharpoonup> (Rust) "'! _"

end
