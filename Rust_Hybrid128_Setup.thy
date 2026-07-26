theory Rust_Hybrid128_Setup
  imports
    Rust_Integer_Hybrid128_Layer
    "HOL-Library.Code_Target_Nat"
begin

text \<open>
  Exact hybrid numeric profile: integer and int use i128 with a BigInt overflow
  variant; nat uses u128 with a BigUint overflow variant.
\<close>

definition rust_integer_power :: "integer \<Rightarrow> nat \<Rightarrow> integer" where
  "rust_integer_power x n = x ^ n"

definition rust_nat_power :: "nat \<Rightarrow> nat \<Rightarrow> nat" where
  "rust_nat_power x n = x ^ n"

lemma [code_unfold]: "(x :: integer) ^ n = rust_integer_power x n"
  by (simp add: rust_integer_power_def)

lemma [code_unfold]: "(x :: nat) ^ n = rust_nat_power x n"
  by (simp add: rust_nat_power_def)

text \<open>
  The natural-number half of the hybrid native representation.  Values through
  \<^verbatim>\<open>u128::MAX\<close> remain allocation-free; larger values use a
  boxed \<^verbatim>\<open>BigUint\<close>.  Conversions to and from
  \<^typ>\<open>integer\<close> are the only boundary between the unsigned and signed
  hybrid representations.
\<close>

code_identifier
  code_module Code_Target_Nat \<rightharpoonup> (Rust) Arith

code_printing code_module Rust_Native_Nat \<rightharpoonup> (Rust) \<open>
use num_bigint::{BigInt, BigUint, Sign};
use num_traits::{ToPrimitive as _, Zero as _};
use std::cmp::Ordering;
use std::ops::{Add, Div, Mul, Rem, Sub};

use crate::Rust_Native_Int::{normalize as normalize_int, RustInt};

#[derive(Debug)]
pub enum RustNat {
    Small(u128),
    Big(Box<BigUint>),
}

impl RustNat {
    pub const ZERO: Self = Self::Small(0);
    pub const ONE: Self = Self::Small(1);

    #[inline(always)]
    pub const fn from_u128(value: u128) -> Self {
        Self::Small(value)
    }

    #[inline]
    pub fn from_biguint(value: BigUint) -> Self {
        normalize_nat(value)
    }

    #[inline]
    pub fn into_biguint(self) -> BigUint {
        match self {
            Self::Small(value) => BigUint::from(value),
            Self::Big(value) => *value,
        }
    }

    #[inline(always)]
    pub fn is_zero(&self) -> bool {
        matches!(self, Self::Small(0))
    }

    #[inline]
    pub fn to_usize(&self) -> Option<usize> {
        match self {
            Self::Small(value) => usize::try_from(*value).ok(),
            Self::Big(value) => value.to_usize(),
        }
    }
}

#[inline]
pub fn normalize_nat(value: BigUint) -> RustNat {
    match value.to_u128() {
        Some(small) => RustNat::Small(small),
        None => RustNat::Big(Box::new(value)),
    }
}

impl Clone for RustNat {
    #[inline(always)]
    fn clone(&self) -> Self {
        match self {
            Self::Small(value) => Self::Small(*value),
            Self::Big(value) => Self::Big(Box::new((**value).clone())),
        }
    }
}

impl PartialEq for RustNat {
    #[inline]
    fn eq(&self, other: &Self) -> bool {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => a == b,
            (Self::Big(a), Self::Big(b)) => a == b,
            _ => false,
        }
    }
}

impl Eq for RustNat {}

impl Ord for RustNat {
    #[inline]
    fn cmp(&self, other: &Self) -> Ordering {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => a.cmp(b),
            (Self::Big(a), Self::Big(b)) => a.cmp(b),
            (Self::Small(_), Self::Big(_)) => Ordering::Less,
            (Self::Big(_), Self::Small(_)) => Ordering::Greater,
        }
    }
}

impl PartialOrd for RustNat {
    #[inline(always)]
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Add for RustNat {
    type Output = Self;

    #[inline]
    fn add(self, other: Self) -> Self {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => match a.checked_add(b) {
                Some(result) => Self::Small(result),
                None => normalize_nat(BigUint::from(a) + BigUint::from(b)),
            },
            (a, b) => normalize_nat(a.into_biguint() + b.into_biguint()),
        }
    }
}

impl Sub for RustNat {
    type Output = Self;

    #[inline]
    fn sub(self, other: Self) -> Self {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => Self::Small(a.saturating_sub(b)),
            (Self::Small(_), Self::Big(_)) => Self::ZERO,
            (Self::Big(a), Self::Small(b)) => {
                normalize_nat(*a - BigUint::from(b))
            }
            (Self::Big(a), Self::Big(b)) => {
                if a <= b { Self::ZERO } else { normalize_nat(*a - *b) }
            }
        }
    }
}

impl Mul for RustNat {
    type Output = Self;

    #[inline]
    fn mul(self, other: Self) -> Self {
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => match a.checked_mul(b) {
                Some(result) => Self::Small(result),
                None => normalize_nat(BigUint::from(a) * BigUint::from(b)),
            },
            (a, b) => normalize_nat(a.into_biguint() * b.into_biguint()),
        }
    }
}

impl Div for RustNat {
    type Output = Self;

    #[inline]
    fn div(self, other: Self) -> Self {
        if other.is_zero() {
            return Self::ZERO;
        }
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => Self::Small(a / b),
            (a, b) => normalize_nat(a.into_biguint() / b.into_biguint()),
        }
    }
}

impl Rem for RustNat {
    type Output = Self;

    #[inline]
    fn rem(self, other: Self) -> Self {
        if other.is_zero() {
            return self;
        }
        match (self, other) {
            (Self::Small(a), Self::Small(b)) => Self::Small(a % b),
            (a, b) => normalize_nat(a.into_biguint() % b.into_biguint()),
        }
    }
}

#[inline]
pub fn from_int(value: RustInt) -> RustNat {
    match value {
        RustInt::Small(value) => {
            if value <= 0 { RustNat::ZERO } else { RustNat::Small(value as u128) }
        }
        RustInt::Big(value) => match value.to_biguint() {
            Some(value) => normalize_nat(value),
            None => RustNat::ZERO,
        },
    }
}

#[inline]
pub fn into_int(value: RustNat) -> RustInt {
    match value {
        RustNat::Small(value) if value <= i128::MAX as u128 => {
            RustInt::Small(value as i128)
        }
        RustNat::Small(value) => normalize_int(BigInt::from(value)),
        RustNat::Big(value) => {
            normalize_int(BigInt::from_biguint(Sign::Plus, *value))
        }
    }
}

#[inline]
fn shift_amount(value: &RustNat) -> usize {
    value.to_usize().expect("shift count exceeds the target address space")
}

#[inline]
pub fn push_bit_int(amount: RustNat, value: RustInt) -> RustInt {
    let amount = shift_amount(&amount);
    match value {
        RustInt::Small(0) => RustInt::ZERO,
        RustInt::Small(value) if amount <= 126 => {
            match value.checked_mul(1i128 << amount) {
                Some(result) => RustInt::Small(result),
                None => normalize_int(BigInt::from(value) << amount),
            }
        }
        value => normalize_int(value.into_bigint() << amount),
    }
}

#[inline]
pub fn drop_bit_int(amount: RustNat, value: RustInt) -> RustInt {
    let amount = shift_amount(&amount);
    match value {
        RustInt::Small(value) if amount < 128 => RustInt::Small(value >> amount),
        RustInt::Small(value) => RustInt::Small(if value < 0 { -1 } else { 0 }),
        value => normalize_int(value.into_bigint() >> amount),
    }
}

#[inline]
pub fn take_bit_int(amount: RustNat, value: RustInt) -> RustInt {
    let amount = shift_amount(&amount);
    if amount == 0 {
        return RustInt::ZERO;
    }
    match value {
        RustInt::Small(value) if amount <= 127 => {
            RustInt::Small(value & ((1i128 << (amount - 1)) - 1 + (1i128 << (amount - 1))))
        }
        RustInt::Small(value) if value >= 0 => RustInt::Small(value),
        value => {
            let modulus = BigInt::from(1u8) << amount;
            let mut result = value.into_bigint() % &modulus;
            if result.sign() == Sign::Minus {
                result += modulus;
            }
            normalize_int(result)
        }
    }
}

#[inline]
pub fn mask_int(amount: RustNat) -> RustInt {
    let amount = shift_amount(&amount);
    if amount == 0 {
        RustInt::ZERO
    } else if amount <= 127 {
        RustInt::Small((1i128 << (amount - 1)) - 1 + (1i128 << (amount - 1)))
    } else {
        normalize_int((BigInt::from(1u8) << amount) - 1)
    }
}

#[inline(always)]
pub fn set_bit_int(amount: RustNat, value: RustInt) -> RustInt {
    value | push_bit_int(amount, RustInt::ONE)
}

#[inline(always)]
pub fn unset_bit_int(amount: RustNat, value: RustInt) -> RustInt {
    value & !push_bit_int(amount, RustInt::ONE)
}

#[inline(always)]
pub fn flip_bit_int(amount: RustNat, value: RustInt) -> RustInt {
    value ^ push_bit_int(amount, RustInt::ONE)
}

#[inline]
pub fn bit_int(value: RustInt, amount: RustNat) -> bool {
    !take_bit_int(RustNat::ONE, drop_bit_int(amount, value)).is_zero()
}

#[inline]
pub fn push_bit_nat(amount: RustNat, value: RustNat) -> RustNat {
    let amount = shift_amount(&amount);
    match value {
        RustNat::Small(0) => RustNat::ZERO,
        RustNat::Small(value) if amount < 128 => {
            match value.checked_mul(1u128 << amount) {
                Some(result) => RustNat::Small(result),
                None => normalize_nat(BigUint::from(value) << amount),
            }
        }
        value => normalize_nat(value.into_biguint() << amount),
    }
}

#[inline]
pub fn drop_bit_nat(amount: RustNat, value: RustNat) -> RustNat {
    let amount = shift_amount(&amount);
    match value {
        RustNat::Small(value) if amount < 128 => RustNat::Small(value >> amount),
        RustNat::Small(_) => RustNat::ZERO,
        value => normalize_nat(value.into_biguint() >> amount),
    }
}

#[inline]
pub fn take_bit_nat(amount: RustNat, value: RustNat) -> RustNat {
    let amount = shift_amount(&amount);
    match value {
        RustNat::Small(_) if amount == 0 => RustNat::ZERO,
        RustNat::Small(value) if amount < 128 => {
            RustNat::Small(value & ((1u128 << amount) - 1))
        }
        RustNat::Small(value) => RustNat::Small(value),
        value if amount == 0 => RustNat::ZERO,
        value => normalize_nat(value.into_biguint() & ((BigUint::from(1u8) << amount) - 1u8)),
    }
}

#[inline]
pub fn mask_nat(amount: RustNat) -> RustNat {
    let amount = shift_amount(&amount);
    if amount == 0 {
        RustNat::ZERO
    } else if amount < 128 {
        RustNat::Small((1u128 << amount) - 1)
    } else if amount == 128 {
        RustNat::Small(u128::MAX)
    } else {
        normalize_nat((BigUint::from(1u8) << amount) - 1u8)
    }
}

#[inline(always)]
pub fn set_bit_nat(amount: RustNat, value: RustNat) -> RustNat {
    match (value, push_bit_nat(amount, RustNat::ONE)) {
        (RustNat::Small(a), RustNat::Small(b)) => RustNat::Small(a | b),
        (a, b) => normalize_nat(a.into_biguint() | b.into_biguint()),
    }
}

#[inline]
pub fn unset_bit_nat(amount: RustNat, value: RustNat) -> RustNat {
    let amount = shift_amount(&amount);
    match value {
        RustNat::Small(value) if amount < 128 => RustNat::Small(value & !(1u128 << amount)),
        RustNat::Small(value) => RustNat::Small(value),
        value => {
            let bit = BigUint::from(1u8) << amount;
            let value = value.into_biguint();
            if (&value & &bit).is_zero() {
                normalize_nat(value)
            } else {
                normalize_nat(value - bit)
            }
        }
    }
}

#[inline(always)]
pub fn flip_bit_nat(amount: RustNat, value: RustNat) -> RustNat {
    match (value, push_bit_nat(amount, RustNat::ONE)) {
        (RustNat::Small(a), RustNat::Small(b)) => RustNat::Small(a ^ b),
        (a, b) => normalize_nat(a.into_biguint() ^ b.into_biguint()),
    }
}

#[inline]
pub fn bit_nat(value: RustNat, amount: RustNat) -> bool {
    !take_bit_nat(RustNat::ONE, drop_bit_nat(amount, value)).is_zero()
}

#[inline]
pub fn pow_int(mut base: RustInt, mut exponent: RustNat) -> RustInt {
    let mut result = RustInt::ONE;
    while !exponent.is_zero() {
        if bit_nat(exponent.clone(), RustNat::ZERO) {
            result = result * base.clone();
        }
        exponent = drop_bit_nat(RustNat::ONE, exponent);
        if !exponent.is_zero() {
            base = base.clone() * base;
        }
    }
    result
}

#[inline]
pub fn pow_nat(mut base: RustNat, mut exponent: RustNat) -> RustNat {
    let mut result = RustNat::ONE;
    while !exponent.is_zero() {
        if bit_nat(exponent.clone(), RustNat::ZERO) {
            result = result * base.clone();
        }
        exponent = drop_bit_nat(RustNat::ONE, exponent);
        if !exponent.is_zero() {
            base = base.clone() * base;
        }
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::mem::{align_of, size_of};

    fn biguint(value: RustNat) -> BigUint {
        value.into_biguint()
    }

    #[test]
    fn small_representation_has_a_bounded_layout() {
        let size = size_of::<RustNat>();
        let align = align_of::<RustNat>();
        eprintln!("RustNat layout: size={size}, align={align}");
        assert!(size <= 32);
        assert!(align <= 16);
    }

    #[test]
    fn promotes_above_u128_and_demotes_after_subtraction() {
        let promoted = RustNat::Small(u128::MAX) + RustNat::ONE;
        assert!(matches!(promoted, RustNat::Big(_)));
        assert_eq!(
            biguint(promoted.clone()),
            (BigUint::from(1u8) << 128usize)
        );
        let demoted = promoted - RustNat::ONE;
        assert!(matches!(demoted, RustNat::Small(value) if value == u128::MAX));
    }

    #[test]
    fn natural_subtraction_saturates_and_big_subtraction_normalizes() {
        assert!(matches!(
            RustNat::Small(3) - RustNat::Small(7),
            RustNat::Small(0)
        ));
        let large = normalize_nat((BigUint::from(1u8) << 128usize) + 7u8);
        let result = large - RustNat::Small(8);
        assert!(matches!(result, RustNat::Small(value) if value == u128::MAX));
    }

    #[test]
    fn unsigned_high_half_round_trips_through_rust_int() {
        for value in [1u128 << 127, u128::MAX] {
            let signed_container = into_int(RustNat::Small(value));
            assert!(matches!(signed_container, RustInt::Big(_)));
            let round_trip = from_int(signed_container);
            assert!(matches!(round_trip, RustNat::Small(result) if result == value));
        }
        assert!(matches!(from_int(RustInt::Small(-1)), RustNat::Small(0)));
    }

    #[test]
    fn shifts_and_masks_cross_the_primitive_boundary_exactly() {
        assert!(matches!(mask_nat(RustNat::Small(128)), RustNat::Small(u128::MAX)));
        assert_eq!(
            biguint(push_bit_nat(RustNat::Small(128), RustNat::ONE)),
            BigUint::from(1u8) << 128usize
        );
        assert!(matches!(
            take_bit_nat(RustNat::Small(128), RustNat::Small(u128::MAX)),
            RustNat::Small(u128::MAX)
        ));

        assert_eq!(
            push_bit_int(RustNat::Small(127), RustInt::Small(-1)).into_bigint(),
            -(BigInt::from(1u8) << 127usize)
        );
        assert_eq!(
            take_bit_int(RustNat::Small(128), RustInt::Small(-1)).into_bigint(),
            (BigInt::from(1u8) << 128usize) - 1
        );
    }

    #[test]
    fn power_uses_native_values_and_promotes_only_when_needed() {
        assert!(matches!(
            pow_nat(RustNat::Small(3), RustNat::Small(4)),
            RustNat::Small(81)
        ));
        assert_eq!(
            pow_int(RustInt::Small(2), RustNat::Small(127)).into_bigint(),
            BigInt::from(1u8) << 127usize
        );
    }
}
\<close>

code_reserved (Rust) Rust_Native_Nat RustNat

code_printing
  type_constructor nat \<rightharpoonup>
    (Rust) "crate::Rust'_Native'_Nat::RustNat"
| constant Code_Target_Nat.Nat \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::from'_int'(_')"
| constant Code_Numeral.nat_of_integer \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::from'_int'(_')"
| constant integer_of_nat \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::into'_int'(_')"
| constant "0 :: nat" \<rightharpoonup>
    (Rust) "crate::Rust'_Native'_Nat::RustNat::ZERO"
| constant "plus :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 9 "+"
| constant "minus :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 9 "-"
| constant "times :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 10 "*"
| constant "divide :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 10 "/"
| constant "modulo :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) infixl 10 "%"
| constant "HOL.equal :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "=="
| constant "less_eq :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<="
| constant "less :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<"
| constant rust_integer_power \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::pow'_int'(_, _')"
| constant rust_nat_power \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::pow'_nat'(_, _')"
| constant "Bit_Operations.push_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::push'_bit'_int'(_, _')"
| constant "Bit_Operations.drop_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::drop'_bit'_int'(_, _')"
| constant "Bit_Operations.take_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::take'_bit'_int'(_, _')"
| constant "Bit_Operations.mask :: nat \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::mask'_int'(_')"
| constant "Bit_Operations.set_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::set'_bit'_int'(_, _')"
| constant "Bit_Operations.unset_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::unset'_bit'_int'(_, _')"
| constant "Bit_Operations.flip_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::flip'_bit'_int'(_, _')"
| constant "Bit_Operations.bit :: integer \<Rightarrow> nat \<Rightarrow> bool" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::bit'_int'(_, _')"
| constant "Bit_Operations.push_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::push'_bit'_nat'(_, _')"
| constant "Bit_Operations.drop_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::drop'_bit'_nat'(_, _')"
| constant "Bit_Operations.take_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::take'_bit'_nat'(_, _')"
| constant "Bit_Operations.mask :: nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::mask'_nat'(_')"
| constant "Bit_Operations.set_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::set'_bit'_nat'(_, _')"
| constant "Bit_Operations.unset_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::unset'_bit'_nat'(_, _')"
| constant "Bit_Operations.flip_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::flip'_bit'_nat'(_, _')"
| constant "Bit_Operations.bit :: nat \<Rightarrow> nat \<Rightarrow> bool" \<rightharpoonup>
    (Rust) "!crate::Rust'_Native'_Nat::bit'_nat'(_, _')"

end
