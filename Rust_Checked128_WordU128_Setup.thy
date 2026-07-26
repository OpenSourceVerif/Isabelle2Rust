theory Rust_Checked128_WordU128_Setup
  imports
    Rust_Checked128_Setup
    "HOL-Library.Word"
begin

text \<open>
  Optional word layer for the Checked128 profile.  Word widths from 1 through
  128 use a Copy u128 payload; integer, int, and nat remain the raw i128/u128
  types selected by \<^theory_text>\<open>Rust_Checked128_Setup\<close>.
\<close>

definition rust_checked_word_power :: "'a::len word \<Rightarrow> nat \<Rightarrow> 'a word" where
  "rust_checked_word_power x n = x ^ n"

lemma [code_unfold]: "(x :: 'a::len word) ^ n = rust_checked_word_power x n"
  by (simp add: rust_checked_word_power_def)

code_printing code_module Rust_Word \<rightharpoonup> (Rust) \<open>
use std::marker::PhantomData;

#[derive(Clone)]
pub enum Itself<A> {
    Type(PhantomData<A>),
}

#[inline(always)]
pub fn type_witness<A>() -> Itself<A> {
    Itself::Type(PhantomData)
}

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
    AbsBit0(i128, PhantomData<A>),
}

#[derive(Clone)]
pub enum Bit1<A> {
    AbsBit1(i128, PhantomData<A>),
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
    fn len_of(witness: Itself<Self>) -> u128
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
    assert!(
        width >= 1 && width <= 128,
        "Rust u128 word adapter supports widths from 1 through 128 bits"
    );
    width
}

#[inline(always)]
const fn mask<W: WordWidth>() -> u128 {
    let width = width::<W>();
    if width == 128 { u128::MAX } else { (1u128 << width) - 1 }
}

#[inline(always)]
fn shift_amount(value: u128) -> u32 {
    u32::try_from(value).unwrap_or(u32::MAX)
}

impl<W: WordWidth> RustWord<W> {
    #[inline(always)]
    pub fn from_bits(bits: u128) -> Self {
        Self {
            bits: bits & mask::<W>(),
            marker: PhantomData,
        }
    }

    #[inline(always)]
    pub fn from_int(value: i128) -> Self {
        Self::from_bits(value as u128)
    }

    #[inline(always)]
    pub fn from_nat(value: u128) -> Self {
        Self::from_bits(value)
    }
}

#[inline(always)]
pub fn to_int<W>(word: RustWord<W>) -> i128 {
    i128::try_from(word.bits)
        .expect("unsigned word value exceeds Checked128 i128")
}

#[inline(always)]
pub fn to_nat<W>(word: RustWord<W>) -> u128 {
    word.bits
}

#[inline(always)]
pub fn to_signed_int<W: WordWidth>(word: RustWord<W>) -> i128 {
    let width = width::<W>();
    if width == 128 {
        word.bits as i128
    } else {
        let sign = 1u128 << (width - 1);
        let extended =
            if word.bits & sign == 0 { word.bits } else { word.bits | (u128::MAX << width) };
        extended as i128
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
pub fn pow<W: WordWidth>(mut base: RustWord<W>, mut exponent: u128) -> RustWord<W> {
    let mut result = one::<W>();
    while exponent != 0 {
        if exponent & 1 == 1 {
            result = mul(result, base);
        }
        exponent >>= 1;
        if exponent != 0 {
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
pub fn push_bit<W: WordWidth>(amount: u128, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(amount);
    if shift >= width::<W>() { zero() } else { RustWord::<W>::from_bits(word.bits << shift) }
}

#[inline(always)]
pub fn drop_bit<W: WordWidth>(amount: u128, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(amount);
    if shift >= width::<W>() { zero() } else { RustWord::<W>::from_bits(word.bits >> shift) }
}

#[inline(always)]
pub fn take_bit<W: WordWidth>(amount: u128, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(amount);
    if shift >= width::<W>() {
        word
    } else if shift == 0 {
        zero()
    } else {
        RustWord::<W>::from_bits(word.bits & ((1u128 << shift) - 1))
    }
}

#[inline(always)]
pub fn word_mask<W: WordWidth>(amount: u128) -> RustWord<W> {
    let shift = shift_amount(amount);
    if shift >= width::<W>() {
        RustWord::<W>::from_bits(mask::<W>())
    } else if shift == 0 {
        zero()
    } else {
        RustWord::<W>::from_bits((1u128 << shift) - 1)
    }
}

#[inline(always)]
pub fn set_bit<W: WordWidth>(amount: u128, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(amount);
    if shift >= width::<W>() { word } else { RustWord::<W>::from_bits(word.bits | (1u128 << shift)) }
}

#[inline(always)]
pub fn unset_bit<W: WordWidth>(amount: u128, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(amount);
    if shift >= width::<W>() { word } else { RustWord::<W>::from_bits(word.bits & !(1u128 << shift)) }
}

#[inline(always)]
pub fn flip_bit<W: WordWidth>(amount: u128, word: RustWord<W>) -> RustWord<W> {
    let shift = shift_amount(amount);
    if shift >= width::<W>() { word } else { RustWord::<W>::from_bits(word.bits ^ (1u128 << shift)) }
}

#[inline(always)]
pub fn bit<W: WordWidth>(word: RustWord<W>, amount: u128) -> bool {
    let shift = shift_amount(amount);
    shift < width::<W>() && ((word.bits >> shift) & 1) == 1
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
| constant rust_checked_word_power \<rightharpoonup>
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
