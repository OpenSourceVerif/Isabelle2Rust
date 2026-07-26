theory Rust_Hybrid128_WordU128_Setup
  imports
    Rust_Hybrid128_Setup
    "HOL-Library.Word"
begin

text \<open>
  A Rust adaptation for Isabelle words of widths from 1 through 128 bits,
  combined with the hybrid native integer and natural-number setup.  Words
  retain their type-level width but store only a primitive \<^verbatim>\<open>u128\<close>
  payload.  Small integer and natural-number conversions use primitive casts
  and masking; only the respective big variants perform arbitrary-precision
  modulo operations.
\<close>

definition rust_native_word_power :: "'a::len word \<Rightarrow> nat \<Rightarrow> 'a word" where
  "rust_native_word_power x n = x ^ n"

lemma [code_unfold]: "(x :: 'a::len word) ^ n = rust_native_word_power x n"
  by (simp add: rust_native_word_power_def)

code_printing code_module Rust_Word \<rightharpoonup> (Rust) \<open>
use num_bigint::{BigInt, BigUint};
use num_traits::{Signed as _, ToPrimitive as _};
use std::marker::PhantomData;

use crate::Rust_Native_Int::RustInt;
use crate::Rust_Native_Nat::RustNat;

#[derive(Clone)]
pub enum Itself<A> {
    Type(PhantomData<A>),
}

#[inline(always)]
pub fn type_witness<A>() -> Itself<A> {
    Itself::Type(PhantomData)
}

// These types mirror Isabelle's type-level numeral constructors.  RustWord
// mentions them only through PhantomData, so they do not enlarge its payload.
#[derive(Clone)]
pub enum Num0 {
    Num0,
}

#[derive(Clone)]
pub enum Num1 {
    OneNum1,
}

#[derive(Clone)]
pub enum Bit0<A> {
    AbsBit0(RustInt, PhantomData<A>),
}

#[derive(Clone)]
pub enum Bit1<A> {
    AbsBit1(RustInt, PhantomData<A>),
}

#[derive(Clone)]
pub struct Signed<A>(pub PhantomData<A>);

// NativeWordWidth is deliberately separate from the generated len_of method.
// Monomorphisation exposes WIDTH to rustc as an associated constant, while
// len_of remains available to generated Isabelle code and returns RustNat.
pub trait NativeWordWidth {
    const WIDTH: u32;
}

impl NativeWordWidth for Num0 {
    const WIDTH: u32 = 0;
}

impl NativeWordWidth for Num1 {
    const WIDTH: u32 = 1;
}

impl<A: NativeWordWidth> NativeWordWidth for Bit0<A> {
    const WIDTH: u32 = 2 * A::WIDTH;
}

impl<A: NativeWordWidth> NativeWordWidth for Bit1<A> {
    const WIDTH: u32 = 2 * A::WIDTH + 1;
}

impl<A: NativeWordWidth> NativeWordWidth for Signed<A> {
    const WIDTH: u32 = A::WIDTH;
}

pub trait WordWidth: NativeWordWidth {
    fn len_of(witness: Itself<Self>) -> RustNat
    where
        Self: Sized;
}

pub struct RustWord<W> {
    bits: u128,
    marker: PhantomData<W>,
}

impl<W> Copy for RustWord<W> {}

impl<W> Clone for RustWord<W> {
    #[inline(always)]
    fn clone(&self) -> Self {
        *self
    }
}

#[inline(always)]
const fn width<W: WordWidth>() -> u32 {
    let width = <W as NativeWordWidth>::WIDTH;
    assert!(width >= 1 && width <= 128,
        "Rust u128 word adapter supports widths from 1 through 128 bits");
    width
}

#[inline(always)]
const fn mask<W: WordWidth>() -> u128 {
    let width = width::<W>();
    if width == 128 {
        u128::MAX
    } else {
        (1u128 << width) - 1
    }
}

// Every Big RustNat is greater than any supported word width.  Therefore word
// operations may saturate it without converting it to a primitive integer.
#[inline(always)]
fn shift_amount(value: &RustNat) -> u32 {
    match value {
        RustNat::Small(value) => u32::try_from(*value).unwrap_or(u32::MAX),
        RustNat::Big(_) => u32::MAX,
    }
}

impl<W: WordWidth> RustWord<W> {
    #[inline(always)]
    pub fn from_bits(bits: u128) -> Self {
        Self {
            bits: bits & mask::<W>(),
            marker: PhantomData,
        }
    }

    #[cold]
    #[inline(never)]
    fn from_bigint(value: BigInt) -> Self {
        let modulus = BigInt::from(1u8) << width::<W>();
        let mut reduced = value % &modulus;
        if reduced.is_negative() {
            reduced += modulus;
        }
        Self::from_bits(reduced.to_u128().expect("word residue must fit u128"))
    }

    #[cold]
    #[inline(never)]
    fn from_biguint(value: BigUint) -> Self {
        let modulus = BigUint::from(1u8) << width::<W>();
        let reduced = value % modulus;
        Self::from_bits(reduced.to_u128().expect("word residue must fit u128"))
    }

    #[inline]
    pub fn from_int(value: RustInt) -> Self {
        match value {
            RustInt::Small(value) => Self::from_bits(value as u128),
            RustInt::Big(value) => Self::from_bigint(*value),
        }
    }

    #[inline]
    pub fn from_nat(value: RustNat) -> Self {
        match value {
            RustNat::Small(value) => Self::from_bits(value),
            RustNat::Big(value) => Self::from_biguint(*value),
        }
    }
}

#[inline]
pub fn to_int<W>(word: RustWord<W>) -> RustInt {
    if word.bits <= i128::MAX as u128 {
        RustInt::Small(word.bits as i128)
    } else {
        RustInt::from_bigint(BigInt::from(word.bits))
    }
}

#[inline(always)]
pub fn to_nat<W>(word: RustWord<W>) -> RustNat {
    RustNat::Small(word.bits)
}

#[inline]
pub fn to_signed_int<W: WordWidth>(word: RustWord<W>) -> RustInt {
    let width = width::<W>();
    if width == 128 {
        RustInt::Small(word.bits as i128)
    } else {
        let sign = 1u128 << (width - 1);
        let extended = if word.bits & sign == 0 {
            word.bits
        } else {
            word.bits | (u128::MAX << width)
        };
        RustInt::Small(extended as i128)
    }
}

#[inline(always)]
pub fn cast<A: WordWidth, B>(word: RustWord<B>) -> RustWord<A> {
    RustWord::<A>::from_bits(word.bits)
}

#[inline(always)]
pub fn signed_cast<A: WordWidth, B: WordWidth>(word: RustWord<B>) -> RustWord<A> {
    let source_width = width::<B>();
    let source_sign = 1u128 << (source_width - 1);
    let extended = if word.bits & source_sign == 0 || source_width == 128 {
        word.bits
    } else {
        word.bits | (u128::MAX << source_width)
    };
    RustWord::<A>::from_bits(extended)
}

#[inline(always)]
pub fn zero<W: WordWidth>() -> RustWord<W> {
    RustWord::<W>::from_bits(0)
}

#[inline(always)]
pub fn one<W: WordWidth>() -> RustWord<W> {
    RustWord::<W>::from_bits(1)
}

#[inline(always)]
pub fn add<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits.wrapping_add(b.bits))
}

#[inline(always)]
pub fn sub<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits.wrapping_sub(b.bits))
}

#[inline(always)]
pub fn mul<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits.wrapping_mul(b.bits))
}

#[inline]
pub fn pow<W: WordWidth>(mut base: RustWord<W>, mut exponent: RustNat) -> RustWord<W> {
    let mut result = one::<W>();
    while !exponent.is_zero() {
        let odd = match &exponent {
            RustNat::Small(value) => value & 1 == 1,
            RustNat::Big(value) => value.bit(0),
        };
        if odd {
            result = mul(result, base);
        }
        exponent = match exponent {
            RustNat::Small(value) => RustNat::Small(value >> 1),
            RustNat::Big(value) => RustNat::from_biguint(*value >> 1usize),
        };
        if !exponent.is_zero() {
            base = mul(base, base);
        }
    }
    result
}

#[inline(always)]
pub fn neg<W: WordWidth>(word: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(word.bits.wrapping_neg())
}

#[inline(always)]
pub fn div<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    if b.bits == 0 { zero() } else { RustWord::<W>::from_bits(a.bits / b.bits) }
}

#[inline(always)]
pub fn rem<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    if b.bits == 0 { a } else { RustWord::<W>::from_bits(a.bits % b.bits) }
}

#[inline(always)]
pub fn equal<W>(a: RustWord<W>, b: RustWord<W>) -> bool {
    a.bits == b.bits
}

#[inline(always)]
pub fn less<W>(a: RustWord<W>, b: RustWord<W>) -> bool {
    a.bits < b.bits
}

#[inline(always)]
pub fn less_eq<W>(a: RustWord<W>, b: RustWord<W>) -> bool {
    a.bits <= b.bits
}

#[inline(always)]
fn signed_key<W: WordWidth>(word: RustWord<W>) -> u128 {
    word.bits ^ (1u128 << (width::<W>() - 1))
}

#[inline(always)]
pub fn signed_less<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> bool {
    signed_key(a) < signed_key(b)
}

#[inline(always)]
pub fn signed_less_eq<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> bool {
    signed_key(a) <= signed_key(b)
}

#[inline(always)]
pub fn bitand<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits & b.bits)
}

#[inline(always)]
pub fn bitor<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits | b.bits)
}

#[inline(always)]
pub fn bitxor<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits ^ b.bits)
}

#[inline(always)]
pub fn bitnot<W: WordWidth>(word: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(!word.bits)
}

#[inline(always)]
pub fn push_bit<W: WordWidth>(amount: RustNat, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&amount);
    if shift >= width::<W>() {
        zero()
    } else {
        RustWord::<W>::from_bits(word.bits << shift)
    }
}

#[inline(always)]
pub fn drop_bit<W: WordWidth>(amount: RustNat, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&amount);
    if shift >= width::<W>() {
        zero()
    } else {
        RustWord::<W>::from_bits(word.bits >> shift)
    }
}

#[inline(always)]
pub fn take_bit<W: WordWidth>(amount: RustNat, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&amount);
    if shift >= width::<W>() {
        word
    } else if shift == 0 {
        zero()
    } else {
        RustWord::<W>::from_bits(word.bits & ((1u128 << shift) - 1))
    }
}

#[inline(always)]
pub fn word_mask<W: WordWidth>(amount: RustNat) -> RustWord<W> {
    let shift = shift_amount(&amount);
    if shift >= width::<W>() {
        RustWord::<W>::from_bits(mask::<W>())
    } else if shift == 0 {
        zero()
    } else {
        RustWord::<W>::from_bits((1u128 << shift) - 1)
    }
}

#[inline(always)]
pub fn set_bit<W: WordWidth>(amount: RustNat, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&amount);
    if shift >= width::<W>() {
        word
    } else {
        RustWord::<W>::from_bits(word.bits | (1u128 << shift))
    }
}

#[inline(always)]
pub fn unset_bit<W: WordWidth>(amount: RustNat, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&amount);
    if shift >= width::<W>() {
        word
    } else {
        RustWord::<W>::from_bits(word.bits & !(1u128 << shift))
    }
}

#[inline(always)]
pub fn flip_bit<W: WordWidth>(amount: RustNat, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&amount);
    if shift >= width::<W>() {
        word
    } else {
        RustWord::<W>::from_bits(word.bits ^ (1u128 << shift))
    }
}

#[inline(always)]
pub fn bit<W: WordWidth>(word: RustWord<W>, amount: RustNat) -> bool {
    let shift = shift_amount(&amount);
    shift < width::<W>() && ((word.bits >> shift) & 1) == 1
}

#[cfg(test)]
mod tests {
    use super::*;

    struct W0;
    struct W1;
    struct W8;
    struct W16;
    struct W64;
    struct W128;
    struct W129;
    struct WConstOnly;

    macro_rules! word_width {
        ($marker:ty, $width:expr) => {
            impl NativeWordWidth for $marker {
                const WIDTH: u32 = $width;
            }

            impl WordWidth for $marker {
                fn len_of(_: Itself<Self>) -> RustNat {
                    RustNat::Small($width as u128)
                }
            }
        };
    }

    word_width!(W0, 0u32);
    word_width!(W1, 1u32);
    word_width!(W8, 8u32);
    word_width!(W16, 16u32);
    word_width!(W64, 64u32);
    word_width!(W128, 128u32);
    word_width!(W129, 129u32);

    impl NativeWordWidth for WConstOnly {
        const WIDTH: u32 = 8;
    }

    impl WordWidth for WConstOnly {
        fn len_of(_: Itself<Self>) -> RustNat {
            panic!("word hot paths must not call len_of")
        }
    }

    fn word<W: WordWidth>(bits: u128) -> RustWord<W> {
        RustWord::<W>::from_bits(bits)
    }

    fn bits<W>(word: RustWord<W>) -> u128 {
        word.bits
    }

    #[test]
    fn words_are_copy_u128_payloads_and_use_constant_widths() {
        fn require_copy<A: Copy>() {}
        require_copy::<RustWord<W8>>();
        assert_eq!(std::mem::size_of::<RustWord<W8>>(), 16);
        let a = word::<WConstOnly>(255);
        assert_eq!(bits(add(a, one())), 0);
        assert_eq!(bits(a), 255);
    }

    #[test]
    fn small_boundaries_stay_native_and_big_boundaries_reduce_exactly() {
        assert_eq!(bits(RustWord::<W8>::from_int(RustInt::Small(-1))), 255);
        assert_eq!(bits(RustWord::<W128>::from_nat(RustNat::Small(u128::MAX))), u128::MAX);

        let positive = (BigInt::from(1u8) << 200usize) + 42;
        let negative = -(BigInt::from(1u8) << 200usize) - 1;
        assert_eq!(bits(RustWord::<W8>::from_int(RustInt::from_bigint(positive))), 42);
        assert_eq!(bits(RustWord::<W8>::from_int(RustInt::from_bigint(negative))), 255);

        assert!(matches!(to_int(word::<W8>(255)), RustInt::Small(255)));
        assert!(matches!(to_int(word::<W128>(u128::MAX)), RustInt::Big(_)));
        assert!(matches!(to_nat(word::<W128>(u128::MAX)), RustNat::Small(u128::MAX)));
        assert!(matches!(to_signed_int(word::<W128>(u128::MAX)), RustInt::Small(-1)));
    }

    #[test]
    fn implements_cast_arithmetic_division_comparison_and_bits() {
        let narrowed: RustWord<W8> = cast(word::<W16>(0x12ab));
        let extended: RustWord<W16> = signed_cast(word::<W8>(0x80));
        assert_eq!(bits(narrowed), 0xab);
        assert_eq!(bits(extended), 0xff80);
        assert_eq!(bits(add(word::<W8>(255), one())), 0);
        assert_eq!(bits(sub(zero::<W8>(), one())), 255);
        assert_eq!(bits(mul(word::<W8>(16), word::<W8>(16))), 0);
        assert_eq!(bits(neg(one::<W8>())), 255);
        assert_eq!(bits(pow(word::<W8>(3), RustNat::Small(5))), 243);
        assert_eq!(bits(div(word::<W8>(7), word::<W8>(2))), 3);
        assert_eq!(bits(rem(word::<W8>(7), word::<W8>(2))), 1);
        assert_eq!(bits(div(word::<W8>(7), zero())), 0);
        assert_eq!(bits(rem(word::<W8>(7), zero())), 7);
        assert!(less(word::<W8>(1), word::<W8>(255)));
        assert!(signed_less(word::<W8>(255), word::<W8>(1)));
        assert_eq!(bits(bitand(word::<W8>(0xaa), word::<W8>(0xcc))), 0x88);
        assert_eq!(bits(bitor(word::<W8>(0xaa), word::<W8>(0xcc))), 0xee);
        assert_eq!(bits(bitxor(word::<W8>(0xaa), word::<W8>(0xcc))), 0x66);
        assert_eq!(bits(bitnot(word::<W8>(0xaa))), 0x55);
    }

    #[test]
    fn implements_native_nat_shifts_masks_and_updates() {
        assert_eq!(bits(push_bit(RustNat::Small(7), word::<W8>(1))), 128);
        assert_eq!(bits(push_bit(RustNat::Small(8), word::<W8>(1))), 0);
        assert_eq!(bits(drop_bit(RustNat::Small(7), word::<W8>(128))), 1);
        assert_eq!(bits(take_bit(RustNat::Small(4), word::<W8>(255))), 15);
        assert_eq!(bits(word_mask::<W8>(RustNat::Small(4))), 15);
        assert_eq!(bits(set_bit(RustNat::Small(3), word::<W8>(0))), 8);
        assert_eq!(bits(unset_bit(RustNat::Small(3), word::<W8>(255))), 247);
        assert_eq!(bits(flip_bit(RustNat::Small(3), word::<W8>(0))), 8);
        assert!(bit(word::<W8>(8), RustNat::Small(3)));
        assert!(!bit(word::<W8>(8), RustNat::Big(Box::new(BigUint::from(1u8) << 200usize))));
    }

    #[test]
    fn preserves_u128_high_half_multiplication() {
        let unsigned_a: RustWord<W128> = cast(word::<W64>(u64::MAX as u128));
        let unsigned_b: RustWord<W128> = cast(word::<W64>(2));
        let unsigned_high: RustWord<W64> = cast(drop_bit(
            RustNat::Small(64), mul(unsigned_a, unsigned_b)));
        assert_eq!(bits(unsigned_high), 1);

        let signed_a: RustWord<W128> = signed_cast(word::<W64>((u64::MAX - 1) as u128));
        let signed_b: RustWord<W128> = signed_cast(word::<W64>(3));
        let signed_high: RustWord<W64> = cast(drop_bit(
            RustNat::Small(64), mul(signed_a, signed_b)));
        assert_eq!(bits(signed_high), u64::MAX as u128);
    }

    #[test]
    #[should_panic(expected = "supports widths from 1 through 128 bits")]
    fn rejects_zero_width() {
        let _ = word::<W0>(0);
    }

    #[test]
    #[should_panic(expected = "supports widths from 1 through 128 bits")]
    fn rejects_widths_above_u128() {
        let _ = word::<W129>(0);
    }
}
\<close> for type_constructor word

code_reserved (Rust) Rust_Word RustWord

code_printing
  type_constructor word \<rightharpoonup>
    (Rust) "crate::Rust'_Word::RustWord<_>"
| type_constructor itself \<rightharpoonup>
    (Rust) "crate::Rust'_Word::Itself<_>"
| type_constructor num0 \<rightharpoonup>
    (Rust) "crate::Rust'_Word::Num0"
| type_constructor num1 \<rightharpoonup>
    (Rust) "crate::Rust'_Word::Num1"
| type_constructor bit0 \<rightharpoonup>
    (Rust) "crate::Rust'_Word::Bit0<_>"
| type_constructor bit1 \<rightharpoonup>
    (Rust) "crate::Rust'_Word::Bit1<_>"
| type_class len0 \<rightharpoonup>
    (Rust) "crate::Rust_Word::WordWidth"

code_printing
  constant Pure.type \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::type'_witness'(')"
| constant Word.Word \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::RustWord::from'_int'(_')"
| constant Word.the_int \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::to'_int'(_')"
| constant Word.of_int \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::RustWord::from'_int'(_')"
| constant Word.of_nat \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::RustWord::from'_nat'(_')"
| constant Word.the_nat \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::to'_nat'(_')"
| constant Word.the_signed_int \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::to'_signed'_int'(_')"
| constant Word.cast \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::cast'(_')"
| constant Word.signed_cast \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::signed'_cast'(_')"
| constant "0 :: ('a::len) word" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::zero'(')"
| constant "1 :: ('a::len) word" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::one'(')"
| constant "plus :: ('a::len) word \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::add'(_, _')"
| constant "minus :: ('a::len) word \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::sub'(_, _')"
| constant "times :: ('a::len) word \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::mul'(_, _')"
| constant rust_native_word_power \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::pow'(_, _')"
| constant "uminus :: ('a::len) word \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::neg'(_')"
| constant "divide :: ('a::len) word \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::div'(_, _')"
| constant "modulo :: ('a::len) word \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::rem'(_, _')"
| constant "HOL.equal :: ('a::len) word \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::equal'(_, _')"
| constant "less :: ('a::len) word \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::less'(_, _')"
| constant "less_eq :: ('a::len) word \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::less'_eq'(_, _')"
| constant "Bit_Operations.and :: ('a::len) word \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::bitand'(_, _')"
| constant "Bit_Operations.or :: ('a::len) word \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::bitor'(_, _')"
| constant "Bit_Operations.xor :: ('a::len) word \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::bitxor'(_, _')"
| constant "Bit_Operations.not :: ('a::len) word \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::bitnot'(_')"
| constant "Bit_Operations.push_bit :: nat \<Rightarrow> ('a::len) word \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::push'_bit'(_, _')"
| constant "Bit_Operations.drop_bit :: nat \<Rightarrow> ('a::len) word \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::drop'_bit'(_, _')"
| constant "Bit_Operations.take_bit :: nat \<Rightarrow> ('a::len) word \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::take'_bit'(_, _')"
| constant "Bit_Operations.mask :: nat \<Rightarrow> ('a::len) word" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::word'_mask'(_')"
| constant "Bit_Operations.set_bit :: nat \<Rightarrow> ('a::len) word \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::set'_bit'(_, _')"
| constant "Bit_Operations.unset_bit :: nat \<Rightarrow> ('a::len) word \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::unset'_bit'(_, _')"
| constant "Bit_Operations.flip_bit :: nat \<Rightarrow> ('a::len) word \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::flip'_bit'(_, _')"
| constant "Bit_Operations.bit :: ('a::len) word \<Rightarrow> nat \<Rightarrow> bool" \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::bit'(_, _')"
| constant word_sle \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::signed'_less'_eq'(_, _')"
| constant word_sless \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::signed'_less'(_, _')"

end
