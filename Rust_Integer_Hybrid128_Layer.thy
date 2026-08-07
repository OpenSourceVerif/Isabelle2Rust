theory Rust_Integer_Hybrid128_Layer
  imports
    Rust_Base_Setup
    "HOL-Library.Code_Target_Int"
begin

text \<open>
  An exact, small-value-optimised representation for Isabelle integers.  Values
  in the signed 128-bit range use the allocation-free \<^verbatim>\<open>Small\<close>
  variant.  Arithmetic promotes to \<^verbatim>\<open>BigInt\<close> only on overflow,
  and every operation on a big value normalises its result back to
  \<^verbatim>\<open>Small\<close> whenever possible.

  This is an internal signed-only layer.  Normal clients should import
  \<^theory_text>\<open>Rust_Hybrid128_Setup\<close>, which selects integer, int, and nat
  together.
\<close>

code_identifier
  code_module Int \<rightharpoonup> (Rust) Arith
| code_module Code_Target_Int \<rightharpoonup> (Rust) Arith

code_printing code_module Rust_Native_Int \<rightharpoonup> (Rust) \<open>
use num_bigint::BigInt;
use num_traits::{Signed as _, ToPrimitive as _, Zero as _};
use std::cmp::Ordering;
use std::ops::{Add, BitAnd, BitOr, BitXor, Div, Mul, Neg, Not, Rem, Sub};

#[derive(Debug)]
pub enum RustInt {
    Small(i128),
    Big(Box<BigInt>),
}

impl RustInt {
    pub const ZERO: Self = Self::Small(0);
    pub const ONE: Self = Self::Small(1);

    #[inline(always)]
    pub const fn from_i128(value: i128) -> Self {
        Self::Small(value)
    }

    #[inline]
    pub fn from_bigint(value: BigInt) -> Self {
        normalize(value)
    }

    #[inline]
    pub fn into_bigint(self) -> BigInt {
        match self {
            Self::Small(value) => BigInt::from(value),
            Self::Big(value) => *value,
        }
    }

    #[inline(always)]
    pub fn is_zero(&self) -> bool {
        matches!(self, Self::Small(0))
    }

    #[inline(always)]
    pub fn is_negative(&self) -> bool {
        match self {
            Self::Small(value) => *value < 0,
            Self::Big(value) => value.sign() == num_bigint::Sign::Minus,
        }
    }

    #[inline]
    pub fn abs(self) -> Self {
        match self {
            Self::Small(value) => match value.checked_abs() {
                Some(result) => Self::Small(result),
                None => normalize(BigInt::from(value).abs()),
            },
            Self::Big(value) => normalize(value.abs()),
        }
    }
}

#[inline]
pub fn normalize(value: BigInt) -> RustInt {
    match value.to_i128() {
        Some(small) => RustInt::Small(small),
        None => RustInt::Big(Box::new(value)),
    }
}

impl Clone for RustInt {
    #[inline(always)]
    fn clone(&self) -> Self {
        match self {
            Self::Small(value) => Self::Small(*value),
            Self::Big(value) => Self::Big(Box::new((**value).clone())),
        }
    }
}

impl PartialEq for RustInt {
    #[inline]
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => a == b,
            (Self::Big(a), Self::Big(b)) => a == b,
            _ => false,
        }
    }
}

impl Eq for RustInt {}

impl Ord for RustInt {
    #[inline]
    fn cmp(&self, other: &Self) -> Ordering {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => a.cmp(b),
            (Self::Big(a), Self::Big(b)) => a.cmp(b),
            (Self::Small(a), Self::Big(b)) => BigInt::from(*a).cmp(b),
            (Self::Big(a), Self::Small(b)) => a.as_ref().cmp(&BigInt::from(*b)),
        }
    }
}

impl PartialOrd for RustInt {
    #[inline(always)]
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Add for RustInt {
    type Output = Self;

    #[inline]
    fn add(self, other: Self) -> Self {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => match a.checked_add(b) {
                Some(result) => Self::Small(result),
                None => normalize(BigInt::from(a) + BigInt::from(b)),
            },
            (a, b) => normalize(a.into_bigint() + b.into_bigint()),
        }
    }
}

impl Sub for RustInt {
    type Output = Self;

    #[inline]
    fn sub(self, other: Self) -> Self {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => match a.checked_sub(b) {
                Some(result) => Self::Small(result),
                None => normalize(BigInt::from(a) - BigInt::from(b)),
            },
            (a, b) => normalize(a.into_bigint() - b.into_bigint()),
        }
    }
}

impl Mul for RustInt {
    type Output = Self;

    #[inline]
    fn mul(self, other: Self) -> Self {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => match a.checked_mul(b) {
                Some(result) => Self::Small(result),
                None => normalize(BigInt::from(a) * BigInt::from(b)),
            },
            (a, b) => normalize(a.into_bigint() * b.into_bigint()),
        }
    }
}

impl Neg for RustInt {
    type Output = Self;

    #[inline]
    fn neg(self) -> Self {
        match self {
            Self::Small(value) => match value.checked_neg() {
                Some(result) => Self::Small(result),
                None => normalize(-BigInt::from(value)),
            },
            Self::Big(value) => normalize(-*value),
        }
    }
}

impl BitAnd for RustInt {
    type Output = Self;

    #[inline]
    fn bitand(self, other: Self) -> Self {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => Self::Small(a & b),
            (a, b) => normalize(a.into_bigint() & b.into_bigint()),
        }
    }
}

impl BitOr for RustInt {
    type Output = Self;

    #[inline]
    fn bitor(self, other: Self) -> Self {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => Self::Small(a | b),
            (a, b) => normalize(a.into_bigint() | b.into_bigint()),
        }
    }
}

impl BitXor for RustInt {
    type Output = Self;

    #[inline]
    fn bitxor(self, other: Self) -> Self {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => Self::Small(a ^ b),
            (a, b) => normalize(a.into_bigint() ^ b.into_bigint()),
        }
    }
}

impl Not for RustInt {
    type Output = Self;

    #[inline]
    fn not(self) -> Self {
        match self {
            Self::Small(value) => Self::Small(!value),
            Self::Big(value) => normalize(!*value),
        }
    }
}

// Isabelle integer division rounds towards negative infinity and gives the
// remainder the sign of the divisor.  Rust and num-bigint both truncate towards
// zero, so adjust the non-exact, opposite-sign case explicitly.
#[inline]
pub fn div_mod_floor(dividend: RustInt, divisor: RustInt) -> (RustInt, RustInt) {
    if divisor.is_zero() {
        return (RustInt::ZERO, dividend);
    }

    match (dividend, divisor) {
        (RustInt::Small(a), RustInt::Small(b)) if !(a == i128::MIN && b == -1) => {
            let mut quotient = a / b;
            let mut remainder = a % b;
            if remainder != 0 && ((remainder < 0) != (b < 0)) {
                quotient -= 1;
                remainder += b;
            }
            (RustInt::Small(quotient), RustInt::Small(remainder))
        }
        (a, b) => {
            let dividend = a.into_bigint();
            let divisor = b.into_bigint();
            let mut quotient = &dividend / &divisor;
            let mut remainder = dividend % &divisor;
            if !remainder.is_zero()
                && (remainder.sign() == num_bigint::Sign::Minus)
                    != (divisor.sign() == num_bigint::Sign::Minus)
            {
                quotient -= 1;
                remainder += divisor;
            }
            (normalize(quotient), normalize(remainder))
        }
    }
}

impl Div for RustInt {
    type Output = Self;

    #[inline]
    fn div(self, other: Self) -> Self {
        div_mod_floor(self, other).0
    }
}

impl Rem for RustInt {
    type Output = Self;

    #[inline]
    fn rem(self, other: Self) -> Self {
        div_mod_floor(self, other).1
    }
}

#[inline(always)]
pub fn duplicate(value: RustInt) -> RustInt {
    value.clone() + value
}

#[inline(always)]
pub fn abs(value: RustInt) -> RustInt {
    value.abs()
}

#[inline]
pub fn divmod_abs(dividend: RustInt, divisor: RustInt) -> (RustInt, RustInt) {
    let dividend = dividend.abs();
    let divisor = divisor.abs();
    if divisor.is_zero() {
        (RustInt::ZERO, dividend)
    } else {
        // Both operands are non-negative, so truncating division is the required
        // absolute-value division and no sign adjustment is needed.
        match (dividend, divisor) {
            (RustInt::Small(a), RustInt::Small(b)) => {
                (RustInt::Small(a / b), RustInt::Small(a % b))
            }
            (a, b) => {
                let dividend = a.into_bigint();
                let divisor = b.into_bigint();
                let quotient = &dividend / &divisor;
                let remainder = dividend % divisor;
                (normalize(quotient), normalize(remainder))
            }
        }
    }
}

\<close>

code_reserved (Rust) Rust_Native_Int RustInt

code_printing
  type_constructor "integer" \<rightharpoonup>
    (Rust) "crate::Rust'_Native'_Int::RustInt"
| type_constructor int \<rightharpoonup>
    (Rust) "crate::Rust'_Native'_Int::RustInt"

code_printing
  constant "0 :: integer" \<rightharpoonup>
    (Rust) "crate::Rust'_Native'_Int::RustInt::ZERO"
| constant int_of_integer \<rightharpoonup>
    (Rust) "_"
| constant integer_of_int \<rightharpoonup>
    (Rust) "_"

setup \<open>
let
  val min_i128 = ~ (Integer.pow 127 2)
  val max_i128 = Integer.pow 127 2 - 1

  fun rust_decimal k =
    if k < 0 then "-" ^ Int.toString (~ k) else Int.toString k

  fun int_to_bytes k =
    let
      fun bytes 0 acc = if null acc then [0] else acc
        | bytes n acc = bytes (n div 256) (n mod 256 :: acc)
    in bytes (abs k) [] end

  fun print_native_int _ k =
    if min_i128 <= k andalso k <= max_i128 then
      "crate::Rust_Native_Int::RustInt::Small(" ^ rust_decimal k ^ "i128)"
    else
      let
        val sign = if k < 0 then "Minus" else "Plus"
        val byte_string = String.concatWith ", " (map Int.toString (int_to_bytes k))
      in
        "crate::Rust_Native_Int::RustInt::from_bigint(" ^
        "BigInt::from_bytes_be(Sign::" ^ sign ^ ", &[" ^ byte_string ^ "]))"
      end
in
  Numeral.add_code \<^const_name>\<open>Code_Numeral.Pos\<close> I print_native_int "Rust"
  #> Numeral.add_code \<^const_name>\<open>Code_Numeral.Neg\<close> (~) print_native_int "Rust"
end
\<close>

(** Keep these precedence levels aligned with Rust. **)
code_printing
  constant "plus :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 9 "+"
| constant "uminus :: integer \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!(- _)"
| constant "minus :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 9 "-"
| constant Code_Numeral.dup \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Int::duplicate'(_')"
| constant Code_Numeral.sub \<rightharpoonup>
    (Rust) "panic'!(\"sub\")"
| constant "times :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 10 "*"
| constant "divide :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 10 "/"
| constant "modulo :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 10 "%"
| constant Code_Numeral.divmod_abs \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Int::divmod'_abs'(_, _')"
| constant "HOL.equal :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "=="
| constant "less_eq :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<="
| constant "less :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<"
| constant "abs :: integer \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Int::abs'(_')"
| constant "Bit_Operations.and :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 7 "&"
| constant "Bit_Operations.or :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 5 "|"
| constant "Bit_Operations.xor :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 6 "^"
| constant "Bit_Operations.not :: integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "'! _"

end
