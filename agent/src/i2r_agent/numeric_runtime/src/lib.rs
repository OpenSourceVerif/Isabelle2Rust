//! Mathematical nat/int operations shared by both experiment backends.
//! Select exactly one backend. Public types deliberately never implement Copy.
//! Operators use the same explicit overflow protocol as fallible methods.
#![forbid(unsafe_code)]

#[cfg(any(all(feature = "arbitrary", feature = "checked"), not(any(feature = "arbitrary", feature = "checked"))))]
compile_error!("Select exactly one i2r-numeric backend: arbitrary or checked");

use std::{fmt, ops::*, str::FromStr};
#[cfg(feature = "arbitrary")]
use dashu_int::{IBig, UBig};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum NumericError { Overflow, InvalidInteger }
pub type NumResult<T> = Result<T, NumericError>;
impl fmt::Display for NumericError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(match self {
            Self::Overflow => "I2R_NUMERIC_OVERFLOW",
            Self::InvalidInteger => "I2R_INVALID_INTEGER",
        })
    }
}
impl std::error::Error for NumericError {}
#[inline]
fn value<T>(r: NumResult<T>) -> T { r.unwrap_or_else(|e| panic!("{e}")) }

#[cfg(feature = "arbitrary")]
type Natural = UBig;
#[cfg(feature = "checked")]
type Natural = u128;
#[cfg(feature = "arbitrary")]
type Integer = IBig;
#[cfg(feature = "checked")]
type Integer = i128;

#[repr(transparent)]
#[derive(Clone, Default, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
/// This ownership contract is identical in both backends.
/// ```compile_fail
/// fn requires_copy<T: Copy>() {}
/// requires_copy::<i2r_numeric::Nat>();
/// ```
pub struct Nat(Natural);
#[repr(transparent)]
#[derive(Clone, Default, Debug, PartialEq, Eq, PartialOrd, Ord, Hash)]
/// ```compile_fail
/// fn requires_copy<T: Copy>() {}
/// requires_copy::<i2r_numeric::Int>();
/// ```
pub struct Int(Integer);

macro_rules! formatting {
    ($t:ident) => {
        impl fmt::Display for $t {
            fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result { self.0.fmt(f) }
        }
        impl FromStr for $t {
            type Err = NumericError;
            fn from_str(s: &str) -> NumResult<Self> {
                // Distinguish malformed text from a valid integer outside the backend range.
                let digits = s.strip_prefix('-').or_else(|| s.strip_prefix('+')).unwrap_or(s);
                if digits.is_empty() || !digits.bytes().all(|c| c.is_ascii_digit()) {
                    return Err(NumericError::InvalidInteger);
                }
                s.parse().map(Self).map_err(|_| NumericError::Overflow)
            }
        }
    }
}
formatting!(Nat);
formatting!(Int);

macro_rules! from_unsigned {
    ($($t:ty),*) => { $(impl From<$t> for Nat {
        #[inline] fn from(n: $t) -> Self { Self(Natural::from(n as u128)) }
    })* }
}
from_unsigned!(u8, u16, u32, u64, u128, usize);
macro_rules! from_signed {
    ($($t:ty),*) => { $(impl From<$t> for Int {
        #[inline] fn from(n: $t) -> Self { Self(Integer::from(n as i128)) }
    })* }
}
from_signed!(i8, i16, i32, i64, i128, isize, u8, u16, u32, u64);

impl Nat {
    #[inline] pub fn zero() -> Self { Self::from(0u8) }
    #[inline] pub fn one() -> Self { Self::from(1u8) }
    #[inline] pub fn is_zero(&self) -> bool { self == &Self::zero() }
    #[inline] pub fn try_add(&self, rhs: &Self) -> NumResult<Self> {
        #[cfg(feature = "arbitrary")] { Ok(Self(&self.0 + &rhs.0)) }
        #[cfg(feature = "checked")] { self.0.checked_add(rhs.0).map(Self).ok_or(NumericError::Overflow) }
    }
    #[inline] pub fn try_mul(&self, rhs: &Self) -> NumResult<Self> {
        #[cfg(feature = "arbitrary")] { Ok(Self(&self.0 * &rhs.0)) }
        #[cfg(feature = "checked")] { self.0.checked_mul(rhs.0).map(Self).ok_or(NumericError::Overflow) }
    }
    /// HOL natural subtraction truncates at zero; this is not overflow.
    #[inline] pub fn sub_trunc(&self, rhs: &Self) -> Self { self - rhs }
    #[inline] pub fn succ(&self) -> Self { self + &Self::one() }
    #[inline] pub fn try_to_u128(&self) -> NumResult<u128> {
        #[cfg(feature = "arbitrary")] { u128::try_from(&self.0).map_err(|_| NumericError::Overflow) }
        #[cfg(feature = "checked")] { Ok(self.0) }
    }
    #[inline] pub fn try_to_usize(&self) -> NumResult<usize> {
        #[cfg(feature = "arbitrary")] { usize::try_from(&self.0).map_err(|_| NumericError::Overflow) }
        #[cfg(feature = "checked")] { usize::try_from(self.0).map_err(|_| NumericError::Overflow) }
    }
    /// Only use where source semantics clamp a count to a resident container.
    #[inline] pub fn clamped_len(&self, len: usize) -> usize {
        if self >= &Self::from(len) { len } else { value(self.try_to_usize()) }
    }
    #[inline] pub fn try_shl(&self, bits: usize) -> NumResult<Self> {
        #[cfg(feature = "arbitrary")] { Ok(Self(&self.0 << bits)) }
        #[cfg(feature = "checked")] {
            if self.0 == 0 { return Ok(Self::zero()); }
            if bits >= 128 || self.0 > (u128::MAX >> bits) { Err(NumericError::Overflow) }
            else { Ok(Self(self.0 << bits)) }
        }
    }
    #[inline] pub fn shr(&self, bits: usize) -> Self {
        #[cfg(feature = "arbitrary")] { Self(&self.0 >> bits) }
        #[cfg(feature = "checked")] { Self(if bits >= 128 { 0 } else { self.0 >> bits }) }
    }
    pub fn try_pow(&self, mut exponent: u32) -> NumResult<Self> {
        let mut result = Self::one(); let mut base = self.clone();
        while exponent != 0 {
            if exponent & 1 != 0 { result = result.try_mul(&base)?; }
            exponent >>= 1;
            if exponent != 0 { base = base.try_mul(&base)?; }
        }
        Ok(result)
    }
}

impl Int {
    #[inline] pub fn zero() -> Self { Self::from(0i8) }
    #[inline] pub fn one() -> Self { Self::from(1i8) }
    #[inline] pub fn is_zero(&self) -> bool { self == &Self::zero() }
    #[inline] pub fn is_negative(&self) -> bool { self < &Self::zero() }
    #[inline] pub fn try_add(&self, rhs: &Self) -> NumResult<Self> {
        #[cfg(feature = "arbitrary")] { Ok(Self(&self.0 + &rhs.0)) }
        #[cfg(feature = "checked")] { self.0.checked_add(rhs.0).map(Self).ok_or(NumericError::Overflow) }
    }
    #[inline] pub fn try_sub(&self, rhs: &Self) -> NumResult<Self> {
        #[cfg(feature = "arbitrary")] { Ok(Self(&self.0 - &rhs.0)) }
        #[cfg(feature = "checked")] { self.0.checked_sub(rhs.0).map(Self).ok_or(NumericError::Overflow) }
    }
    #[inline] pub fn try_mul(&self, rhs: &Self) -> NumResult<Self> {
        #[cfg(feature = "arbitrary")] { Ok(Self(&self.0 * &rhs.0)) }
        #[cfg(feature = "checked")] { self.0.checked_mul(rhs.0).map(Self).ok_or(NumericError::Overflow) }
    }
    #[inline] pub fn try_neg(&self) -> NumResult<Self> {
        #[cfg(feature = "arbitrary")] { Ok(Self(-&self.0)) }
        #[cfg(feature = "checked")] { self.0.checked_neg().map(Self).ok_or(NumericError::Overflow) }
    }
    #[inline] pub fn try_from_nat(n: &Nat) -> NumResult<Self> {
        #[cfg(feature = "arbitrary")] { Ok(Self(IBig::from(n.0.clone()))) }
        #[cfg(feature = "checked")] { i128::try_from(n.0).map(Self).map_err(|_| NumericError::Overflow) }
    }
    /// HOL nat-of-int maps every negative integer to zero.
    #[inline] pub fn to_nat(&self) -> Nat {
        if self.is_negative() { return Nat::zero(); }
        #[cfg(feature = "arbitrary")] { Nat(UBig::try_from(self.0.clone()).expect("nonnegative")) }
        #[cfg(feature = "checked")] { Nat(self.0 as u128) }
    }
    #[inline] pub fn try_to_i128(&self) -> NumResult<i128> {
        #[cfg(feature = "arbitrary")] { i128::try_from(&self.0).map_err(|_| NumericError::Overflow) }
        #[cfg(feature = "checked")] { Ok(self.0) }
    }
    /// Isabelle integer div rounds toward negative infinity, not toward zero.
    #[inline] pub fn try_div_floor(&self, rhs: &Self) -> NumResult<Self> {
        if rhs.is_zero() { return Ok(Self::zero()); }
        #[cfg(feature = "arbitrary")] {
            let q = &self.0 / &rhs.0; let r = &self.0 % &rhs.0;
            Ok(Self(if r != IBig::from(0i8) && self.is_negative() != rhs.is_negative() { q - IBig::from(1i8) } else { q }))
        }
        #[cfg(feature = "checked")] {
            let q = self.0.checked_div(rhs.0).ok_or(NumericError::Overflow)?;
            let r = self.0 % rhs.0;
            Ok(Self(if r != 0 && (self.0 < 0) != (rhs.0 < 0) { q - 1 } else { q }))
        }
    }
    /// The remainder has the divisor's sign; a mod 0 = a.
    #[inline] pub fn mod_floor(&self, rhs: &Self) -> Self {
        if rhs.is_zero() { return self.clone(); }
        #[cfg(feature = "arbitrary")] {
            let r = &self.0 % &rhs.0;
            Self(if r != IBig::from(0i8) && self.is_negative() != rhs.is_negative() { r + &rhs.0 } else { r })
        }
        #[cfg(feature = "checked")] {
            // MIN mod -1 is zero even though the quotient is unrepresentable.
            if rhs.0 == -1 { return Self::zero(); }
            let r = self.0 % rhs.0;
            Self(if r != 0 && (self.0 < 0) != (rhs.0 < 0) { r + rhs.0 } else { r })
        }
    }
}

// Preserve owned/borrowed overloads in both backends. In arbitrary mode owned
// addition/multiplication can reuse Dashu allocations; no mandatory clone shim.
macro_rules! arithmetic {
    ($t:ident, $trait:ident, $method:ident, $op:tt, $checked:ident) => {
        impl $trait<$t> for $t { type Output = $t;
            #[inline] fn $method(self, rhs: $t) -> $t {
                #[cfg(feature = "arbitrary")] { $t(self.0 $op rhs.0) }
                #[cfg(feature = "checked")] { $t(value(self.0.$checked(rhs.0).ok_or(NumericError::Overflow))) }
            }
        }
        impl $trait<&$t> for $t { type Output = $t;
            #[inline] fn $method(self, rhs: &$t) -> $t {
                #[cfg(feature = "arbitrary")] { $t(self.0 $op &rhs.0) }
                #[cfg(feature = "checked")] { $t(value(self.0.$checked(rhs.0).ok_or(NumericError::Overflow))) }
            }
        }
        impl $trait<$t> for &$t { type Output = $t;
            #[inline] fn $method(self, rhs: $t) -> $t {
                #[cfg(feature = "arbitrary")] { $t(&self.0 $op rhs.0) }
                #[cfg(feature = "checked")] { $t(value(self.0.$checked(rhs.0).ok_or(NumericError::Overflow))) }
            }
        }
        impl $trait<&$t> for &$t { type Output = $t;
            #[inline] fn $method(self, rhs: &$t) -> $t {
                #[cfg(feature = "arbitrary")] { $t(&self.0 $op &rhs.0) }
                #[cfg(feature = "checked")] { $t(value(self.0.$checked(rhs.0).ok_or(NumericError::Overflow))) }
            }
        }
    }
}
arithmetic!(Nat, Add, add, +, checked_add);
arithmetic!(Nat, Mul, mul, *, checked_mul);
arithmetic!(Int, Add, add, +, checked_add);
arithmetic!(Int, Sub, sub, -, checked_sub);
arithmetic!(Int, Mul, mul, *, checked_mul);

macro_rules! natural_total {
    ($trait:ident, $method:ident, $op:tt, $guard:expr, $fallback:expr) => {
        impl $trait<Nat> for Nat { type Output = Nat;
            #[inline] fn $method(self, rhs: Nat) -> Nat { if $guard(&self,&rhs) { $fallback(self) } else { Nat(self.0 $op rhs.0) } }
        }
        impl $trait<&Nat> for Nat { type Output = Nat;
            #[inline] fn $method(self, rhs: &Nat) -> Nat {
                if $guard(&self,rhs) { return $fallback(self); }
                #[cfg(feature = "arbitrary")] { Nat(self.0 $op &rhs.0) }
                #[cfg(feature = "checked")] { Nat(self.0 $op rhs.0) }
            }
        }
        impl $trait<Nat> for &Nat { type Output = Nat;
            #[inline] fn $method(self, rhs: Nat) -> Nat {
                if $guard(self,&rhs) { return $fallback(self.clone()); }
                #[cfg(feature = "arbitrary")] { Nat(&self.0 $op rhs.0) }
                #[cfg(feature = "checked")] { Nat(self.0 $op rhs.0) }
            }
        }
        impl $trait<&Nat> for &Nat { type Output = Nat;
            #[inline] fn $method(self, rhs: &Nat) -> Nat {
                if $guard(self,rhs) { return $fallback(self.clone()); }
                #[cfg(feature = "arbitrary")] { Nat(&self.0 $op &rhs.0) }
                #[cfg(feature = "checked")] { Nat(self.0 $op rhs.0) }
            }
        }
    }
}
natural_total!(Sub, sub, -, |a: &Nat, b: &Nat| a < b, |_: Nat| Nat::zero());
natural_total!(Div, div, /, |_: &Nat, b: &Nat| b.is_zero(), |_: Nat| Nat::zero());
natural_total!(Rem, rem, %, |_: &Nat, b: &Nat| b.is_zero(), |a: Nat| a);

macro_rules! signed_total {
    ($trait:ident, $method:ident, $body:expr) => {
        impl $trait<&Int> for &Int { type Output = Int;
            #[inline] fn $method(self, rhs: &Int) -> Int { $body(self,rhs) } }
        impl $trait<Int> for Int { type Output = Int;
            #[inline] fn $method(self, rhs: Int) -> Int { $body(&self,&rhs) } }
        impl $trait<&Int> for Int { type Output = Int;
            #[inline] fn $method(self, rhs: &Int) -> Int { $body(&self,rhs) } }
        impl $trait<Int> for &Int { type Output = Int;
            #[inline] fn $method(self, rhs: Int) -> Int { $body(self,&rhs) } }
    }
}
signed_total!(Div, div, |a: &Int,b: &Int| value(a.try_div_floor(b)));
signed_total!(Rem, rem, |a: &Int,b: &Int| a.mod_floor(b));
impl Neg for Int { type Output = Self; #[inline] fn neg(self) -> Self { value(self.try_neg()) } }
impl Neg for &Int { type Output = Int; #[inline] fn neg(self) -> Int { value(self.try_neg()) } }

macro_rules! assignment {
    ($t:ident,$tr:ident,$method:ident,$op:tt,$check:ident) => {
        impl $tr<&$t> for $t {
            #[inline] fn $method(&mut self, rhs: &$t) {
                #[cfg(feature = "arbitrary")] { self.0 $op &rhs.0; }
                #[cfg(feature = "checked")] { self.0 = value(self.0.$check(rhs.0).ok_or(NumericError::Overflow)); }
            }
        }
        impl $tr<$t> for $t { #[inline] fn $method(&mut self, rhs: $t) { self.$method(&rhs); } }
    }
}
assignment!(Nat,AddAssign,add_assign,+=,checked_add);
assignment!(Nat,MulAssign,mul_assign,*=,checked_mul);
assignment!(Int,AddAssign,add_assign,+=,checked_add);
assignment!(Int,SubAssign,sub_assign,-=,checked_sub);
assignment!(Int,MulAssign,mul_assign,*=,checked_mul);
