theory Rust_BigInt_WordU128_Setup
  imports
    Rust_BigInt_Setup
    "HOL-Library.Word"
begin

text \<open>
  A Rust adaptation for Isabelle words whose type-level width is at most 128
  bits.  The word payload is a primitive \<^verbatim>\<open>u128\<close>.  The existing
  Isabelle \<^class>\<open>len0\<close> instances implement a small Rust width trait, so no
  width value is stored in a word.  The standard type-level numeral constructors
  additionally provide their width through a Rust associated constant.  The
  generated \<^verbatim>\<open>len_of\<close> methods remain available for compatibility,
  while word hot paths use the constant width and mask.

  This setup deliberately retains Isabelle \<^typ>\<open>int\<close> and \<^typ>\<open>nat\<close> as
  \<^verbatim>\<open>BigInt\<close>.  Conversions at the word boundary preserve the unbounded
  semantics of those types, while word arithmetic stays on \<^verbatim>\<open>u128\<close>.
\<close>

definition rust_word_power :: "'a::len word \<Rightarrow> nat \<Rightarrow> 'a word" where
  "rust_word_power x n = x ^ n"

lemma [code_unfold]: "(x :: 'a::len word) ^ n = rust_word_power x n"
  by (simp add: rust_word_power_def)

code_printing code_module Rust_Word \<rightharpoonup> (Rust) \<open>
use num_bigint::BigInt;
use num_traits::{Signed as _, ToPrimitive as _, Zero as _};
use std::marker::PhantomData;

#[derive(Clone)]
pub enum Itself<A> {
    Type(PhantomData<A>),
}

#[inline]
pub fn type_witness<A>() -> Itself<A> {
    Itself::Type(PhantomData)
}

// These marker types mirror the generated Isabelle datatype shapes.  RustWord
// stores them only through PhantomData, so their value representation is never
// part of a word payload.
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
    AbsBit0(BigInt, PhantomData<A>),
}

#[derive(Clone)]
pub enum Bit1<A> {
    AbsBit1(BigInt, PhantomData<A>),
}

#[derive(Clone)]
pub struct Signed<A>(pub PhantomData<A>);

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
    fn len_of(witness: Itself<Self>) -> BigInt
    where
        Self: Sized;
}

pub struct RustWord<W> {
    bits: u128,
    marker: PhantomData<W>,
}

impl<W> Copy for RustWord<W> {}

impl<W> Clone for RustWord<W> {
    #[inline]
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

#[inline]
fn shift_amount(n: &BigInt) -> u32 {
    n.to_u32().unwrap_or(u32::MAX)
}

impl<W: WordWidth> RustWord<W> {
    #[inline]
    pub fn from_bigint(value: BigInt) -> Self {
        let width = width::<W>();
        let modulus = BigInt::from(1u8) << width;
        let mut reduced = value % &modulus;
        if reduced.is_negative() {
            reduced += &modulus;
        }
        Self {
            bits: reduced.to_u128().expect("word residue must fit u128"),
            marker: PhantomData,
        }
    }

    #[inline]
    pub fn from_bits(bits: u128) -> Self {
        Self {
            bits: bits & mask::<W>(),
            marker: PhantomData,
        }
    }
}

#[inline]
pub fn to_bigint<W>(word: RustWord<W>) -> BigInt {
    BigInt::from(word.bits)
}

#[inline]
pub fn to_signed_bigint<W: WordWidth>(word: RustWord<W>) -> BigInt {
    let width = width::<W>();
    let sign = 1u128 << (width - 1);
    let value = BigInt::from(word.bits);
    if word.bits & sign == 0 {
        value
    } else {
        value - (BigInt::from(1u8) << width)
    }
}

#[inline]
pub fn cast<A: WordWidth, B>(word: RustWord<B>) -> RustWord<A> {
    RustWord::<A>::from_bits(word.bits)
}

#[inline]
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

#[inline]
pub fn zero<W: WordWidth>() -> RustWord<W> {
    RustWord::<W>::from_bits(0)
}

#[inline]
pub fn one<W: WordWidth>() -> RustWord<W> {
    RustWord::<W>::from_bits(1)
}

#[inline]
pub fn add<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits.wrapping_add(b.bits))
}

#[inline]
pub fn sub<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits.wrapping_sub(b.bits))
}

#[inline]
pub fn mul<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits.wrapping_mul(b.bits))
}

#[inline]
pub fn pow<W: WordWidth>(mut base: RustWord<W>, mut exponent: BigInt) -> RustWord<W> {
    let mut result = one::<W>();
    while !exponent.is_zero() {
        if (&exponent & BigInt::from(1u8)) == BigInt::from(1u8) {
            result = mul(result, base);
        }
        exponent >>= 1usize;
        if !exponent.is_zero() {
            base = mul(base, base);
        }
    }
    result
}

#[inline]
pub fn neg<W: WordWidth>(a: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits.wrapping_neg())
}

#[inline]
pub fn div<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    if b.bits == 0 { zero() } else { RustWord::<W>::from_bits(a.bits / b.bits) }
}

#[inline]
pub fn rem<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    if b.bits == 0 { a } else { RustWord::<W>::from_bits(a.bits % b.bits) }
}

#[inline]
pub fn equal<W>(a: RustWord<W>, b: RustWord<W>) -> bool {
    a.bits == b.bits
}

#[inline]
pub fn less<W>(a: RustWord<W>, b: RustWord<W>) -> bool {
    a.bits < b.bits
}

#[inline]
pub fn less_eq<W>(a: RustWord<W>, b: RustWord<W>) -> bool {
    a.bits <= b.bits
}

#[inline]
fn signed_key<W: WordWidth>(word: RustWord<W>) -> u128 {
    word.bits ^ (1u128 << (width::<W>() - 1))
}

#[inline]
pub fn signed_less<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> bool {
    signed_key(a) < signed_key(b)
}

#[inline]
pub fn signed_less_eq<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> bool {
    signed_key(a) <= signed_key(b)
}

#[inline]
pub fn bitand<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits & b.bits)
}

#[inline]
pub fn bitor<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits | b.bits)
}

#[inline]
pub fn bitxor<W: WordWidth>(a: RustWord<W>, b: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(a.bits ^ b.bits)
}

#[inline]
pub fn bitnot<W: WordWidth>(a: RustWord<W>) -> RustWord<W> {
    RustWord::<W>::from_bits(!a.bits)
}

#[inline]
pub fn push_bit<W: WordWidth>(n: BigInt, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&n);
    if shift >= width::<W>() {
        zero()
    } else {
        RustWord::<W>::from_bits(word.bits << shift)
    }
}

#[inline]
pub fn drop_bit<W: WordWidth>(n: BigInt, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&n);
    if shift >= width::<W>() {
        zero()
    } else {
        RustWord::<W>::from_bits(word.bits >> shift)
    }
}

#[inline]
pub fn take_bit<W: WordWidth>(n: BigInt, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&n);
    if shift >= width::<W>() {
        word
    } else if shift == 0 {
        zero()
    } else {
        RustWord::<W>::from_bits(word.bits & ((1u128 << shift) - 1))
    }
}

#[inline]
pub fn word_mask<W: WordWidth>(n: BigInt) -> RustWord<W> {
    let shift = shift_amount(&n);
    if shift >= width::<W>() {
        RustWord::<W>::from_bits(mask::<W>())
    } else if shift == 0 {
        zero()
    } else {
        RustWord::<W>::from_bits((1u128 << shift) - 1)
    }
}

#[inline]
pub fn set_bit<W: WordWidth>(n: BigInt, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&n);
    if shift >= width::<W>() {
        word
    } else {
        RustWord::<W>::from_bits(word.bits | (1u128 << shift))
    }
}

#[inline]
pub fn unset_bit<W: WordWidth>(n: BigInt, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&n);
    if shift >= width::<W>() {
        word
    } else {
        RustWord::<W>::from_bits(word.bits & !(1u128 << shift))
    }
}

#[inline]
pub fn flip_bit<W: WordWidth>(n: BigInt, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(&n);
    if shift >= width::<W>() {
        word
    } else {
        RustWord::<W>::from_bits(word.bits ^ (1u128 << shift))
    }
}

#[inline]
pub fn bit<W: WordWidth>(word: RustWord<W>, n: BigInt) -> bool {
    let shift = shift_amount(&n);
    shift < width::<W>() && ((word.bits >> shift) & 1) == 1
}

#[cfg(test)]
mod tests {
    use super::*;

    struct W0;
    struct W1;
    struct W4;
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
                fn len_of(_: Itself<Self>) -> BigInt {
                    BigInt::from($width)
                }
            }
        };
    }

    word_width!(W0, 0u32);
    word_width!(W1, 1u32);
    word_width!(W4, 4u32);
    word_width!(W8, 8u32);
    word_width!(W16, 16u32);
    word_width!(W64, 64u32);
    word_width!(W128, 128u32);
    word_width!(W129, 129u32);

    impl NativeWordWidth for WConstOnly {
        const WIDTH: u32 = 8;
    }

    impl WordWidth for WConstOnly {
        fn len_of(_: Itself<Self>) -> BigInt {
            panic!("the adapter must use NativeWordWidth::WIDTH")
        }
    }

    fn word<W: WordWidth>(bits: u128) -> RustWord<W> {
        RustWord::<W>::from_bits(bits)
    }

    fn bits<W>(word: RustWord<W>) -> u128 {
        word.bits
    }

    #[test]
    fn words_are_copy_without_a_copy_width_marker() {
        fn require_copy<A: Copy>() {}

        require_copy::<RustWord<W8>>();
        let a = word::<W8>(42);
        let b = a;
        assert_eq!(bits(a), bits(b));
    }

    #[test]
    fn native_marker_widths_cover_even_odd_and_signed_lengths() {
        type W5 = Bit1<Bit0<Num1>>;
        type SignedW5 = Signed<W5>;

        assert_eq!(<Num0 as NativeWordWidth>::WIDTH, 0);
        assert_eq!(<W5 as NativeWordWidth>::WIDTH, 5);
        assert_eq!(<SignedW5 as NativeWordWidth>::WIDTH, 5);
    }

    #[test]
    fn word_hot_paths_do_not_call_len_of() {
        assert_eq!(bits(add(word::<WConstOnly>(255), word::<WConstOnly>(1))), 0);
    }

    #[test]
    fn constructs_converts_and_casts() {
        assert_eq!(bits(word::<W1>(3)), 1);
        assert_eq!(bits(word::<W128>(u128::MAX)), u128::MAX);
        assert_eq!(bits(RustWord::<W8>::from_bigint(BigInt::from(-1))), 255);
        assert_eq!(to_bigint(word::<W8>(255)), BigInt::from(255));
        assert_eq!(to_signed_bigint(word::<W8>(255)), BigInt::from(-1));

        let narrowed: RustWord<W4> = cast(word::<W8>(0xab));
        let widened: RustWord<W16> = cast(word::<W8>(0xab));
        let sign_extended: RustWord<W16> = signed_cast(word::<W8>(0x80));
        assert_eq!(bits(narrowed), 0xb);
        assert_eq!(bits(widened), 0xab);
        assert_eq!(bits(sign_extended), 0xff80);
    }

    #[test]
    fn implements_wrapping_arithmetic_and_zero_division() {
        assert_eq!(bits(zero::<W8>()), 0);
        assert_eq!(bits(one::<W8>()), 1);
        assert_eq!(bits(add(word::<W8>(255), word::<W8>(1))), 0);
        assert_eq!(bits(sub(word::<W8>(0), word::<W8>(1))), 255);
        assert_eq!(bits(mul(word::<W8>(16), word::<W8>(16))), 0);
        assert_eq!(bits(neg(word::<W8>(1))), 255);
        assert_eq!(bits(pow(word::<W8>(3), BigInt::from(5))), 243);
        assert_eq!(bits(div(word::<W8>(7), word::<W8>(2))), 3);
        assert_eq!(bits(rem(word::<W8>(7), word::<W8>(2))), 1);
        assert_eq!(bits(div(word::<W8>(7), zero::<W8>())), 0);
        assert_eq!(bits(rem(word::<W8>(7), zero::<W8>())), 7);
        assert_eq!(bits(add(word::<W128>(u128::MAX), one::<W128>())), 0);
    }

    #[test]
    fn implements_unsigned_signed_and_bitwise_operations() {
        let negative = word::<W8>(255);
        let positive = word::<W8>(1);
        assert!(equal(negative, word::<W8>(255)));
        assert!(!less(negative, positive));
        assert!(less_eq(positive, positive));
        assert!(signed_less(negative, positive));
        assert!(signed_less_eq(negative, negative));

        let a = word::<W8>(0b1010);
        let b = word::<W8>(0b1100);
        assert_eq!(bits(bitand(a, b)), 0b1000);
        assert_eq!(bits(bitor(a, b)), 0b1110);
        assert_eq!(bits(bitxor(a, b)), 0b0110);
        assert_eq!(bits(bitnot(a)), 0b1111_0101);
    }

    #[test]
    fn implements_shifts_masks_and_bit_updates() {
        assert_eq!(bits(push_bit(BigInt::from(7), word::<W8>(1))), 128);
        assert_eq!(bits(push_bit(BigInt::from(8), word::<W8>(1))), 0);
        assert_eq!(bits(drop_bit(BigInt::from(7), word::<W8>(128))), 1);
        assert_eq!(bits(drop_bit(BigInt::from(8), word::<W8>(128))), 0);
        assert_eq!(bits(take_bit(BigInt::from(4), word::<W8>(255))), 15);
        assert_eq!(bits(take_bit(BigInt::from(8), word::<W8>(255))), 255);
        assert_eq!(bits(take_bit(BigInt::from(0), word::<W8>(255))), 0);
        assert_eq!(bits(word_mask::<W8>(BigInt::from(0))), 0);
        assert_eq!(bits(word_mask::<W8>(BigInt::from(4))), 15);
        assert_eq!(bits(word_mask::<W8>(BigInt::from(9))), 255);
        assert_eq!(bits(set_bit(BigInt::from(3), word::<W8>(0))), 8);
        assert_eq!(bits(set_bit(BigInt::from(8), word::<W8>(0))), 0);
        assert_eq!(bits(unset_bit(BigInt::from(3), word::<W8>(255))), 247);
        assert_eq!(bits(flip_bit(BigInt::from(3), word::<W8>(0))), 8);
        assert!(bit(word::<W8>(8), BigInt::from(3)));
        assert!(!bit(word::<W8>(8), BigInt::from(8)));
    }

    #[test]
    fn preserves_the_u128_high_half_multiplication_path() {
        let unsigned_a: RustWord<W128> = cast(word::<W64>(u64::MAX as u128));
        let unsigned_b: RustWord<W128> = cast(word::<W64>(2));
        let unsigned_high: RustWord<W64> = cast(drop_bit(
            BigInt::from(64),
            mul(unsigned_a, unsigned_b),
        ));
        assert_eq!(bits(unsigned_high), 1);

        let signed_a: RustWord<W128> = signed_cast(word::<W64>((u64::MAX - 1) as u128));
        let signed_b: RustWord<W128> = signed_cast(word::<W64>(3));
        let signed_high: RustWord<W64> = cast(drop_bit(
            BigInt::from(64),
            mul(signed_a, signed_b),
        ));
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
    (Rust) "!crate::Rust'_Word::RustWord::from'_bigint'(_')"
| constant Word.the_int \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::to'_bigint'(_')"
| constant Word.of_int \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::RustWord::from'_bigint'(_')"
| constant Word.of_nat \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::RustWord::from'_bigint'(_')"
| constant Word.the_nat \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::to'_bigint'(_')"
| constant Word.the_signed_int \<rightharpoonup>
    (Rust) "!crate::Rust'_Word::to'_signed'_bigint'(_')"
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
| constant rust_word_power \<rightharpoonup>
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
