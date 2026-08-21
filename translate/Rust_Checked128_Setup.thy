theory Rust_Checked128_Setup
  imports
    Rust_Base_Setup
    "HOL-Library.Code_Target_Int"
    "HOL-Library.Code_Target_Nat"
begin

text \<open>
  Bounded numeric profile: integer and int map directly to i128, while nat maps
  directly to u128.  Values are Copy.  Operations that would leave the selected
  primitive range fail explicitly instead of wrapping; natural subtraction
  retains Isabelle's saturation at zero.
\<close>

definition rust_checked_integer_power :: "integer \<Rightarrow> nat \<Rightarrow> integer" where
  "rust_checked_integer_power x n = x ^ n"

definition rust_checked_nat_power :: "nat \<Rightarrow> nat \<Rightarrow> nat" where
  "rust_checked_nat_power x n = x ^ n"

lemma [code_unfold]: "(x :: integer) ^ n = rust_checked_integer_power x n"
  by (simp add: rust_checked_integer_power_def)

lemma [code_unfold]: "(x :: nat) ^ n = rust_checked_nat_power x n"
  by (simp add: rust_checked_nat_power_def)

code_identifier
  code_module Int \<rightharpoonup> (Rust) Arith
| code_module Code_Target_Int \<rightharpoonup> (Rust) Arith
| code_module Code_Target_Nat \<rightharpoonup> (Rust) Arith

code_printing code_module Rust_Checked128 \<rightharpoonup> (Rust) \<open>
#[cold]
#[inline(never)]
fn overflow(operation: &str) -> ! {
    panic!("Isabelle numeric value exceeds Checked128 during {operation}")
}

#[inline(always)]
pub fn add_int(a: i128, b: i128) -> i128 {
    a.checked_add(b).unwrap_or_else(|| overflow("integer addition"))
}

#[inline(always)]
pub fn sub_int(a: i128, b: i128) -> i128 {
    a.checked_sub(b).unwrap_or_else(|| overflow("integer subtraction"))
}

#[inline(always)]
pub fn mul_int(a: i128, b: i128) -> i128 {
    a.checked_mul(b).unwrap_or_else(|| overflow("integer multiplication"))
}

#[inline(always)]
pub fn neg_int(value: i128) -> i128 {
    value.checked_neg().unwrap_or_else(|| overflow("integer negation"))
}

#[inline(always)]
pub fn abs_int(value: i128) -> i128 {
    value.checked_abs().unwrap_or_else(|| overflow("integer absolute value"))
}

#[inline]
pub fn div_mod_floor(dividend: i128, divisor: i128) -> (i128, i128) {
    if divisor == 0 {
        return (0, dividend);
    }
    if dividend == i128::MIN && divisor == -1 {
        overflow("integer division");
    }
    let mut quotient = dividend / divisor;
    let mut remainder = dividend % divisor;
    if remainder != 0 && ((remainder < 0) != (divisor < 0)) {
        quotient = quotient.checked_sub(1).unwrap_or_else(|| overflow("integer division"));
        remainder = remainder
            .checked_add(divisor)
            .unwrap_or_else(|| overflow("integer remainder"));
    }
    (quotient, remainder)
}

#[inline(always)]
pub fn div_int(a: i128, b: i128) -> i128 {
    div_mod_floor(a, b).0
}

#[inline(always)]
pub fn rem_int(a: i128, b: i128) -> i128 {
    div_mod_floor(a, b).1
}

#[inline(always)]
pub fn duplicate(value: i128) -> i128 {
    add_int(value, value)
}

#[inline]
pub fn divmod_abs(a: i128, b: i128) -> (i128, i128) {
    let a = abs_int(a);
    let b = abs_int(b);
    if b == 0 { (0, a) } else { (a / b, a % b) }
}

#[inline(always)]
pub fn from_int(value: i128) -> u128 {
    if value <= 0 { 0 } else { value as u128 }
}

#[inline(always)]
pub fn into_int(value: u128) -> i128 {
    i128::try_from(value).unwrap_or_else(|_| overflow("nat-to-integer conversion"))
}

#[inline(always)]
pub fn add_nat(a: u128, b: u128) -> u128 {
    a.checked_add(b).unwrap_or_else(|| overflow("natural addition"))
}

#[inline(always)]
pub fn sub_nat(a: u128, b: u128) -> u128 {
    a.saturating_sub(b)
}

#[inline(always)]
pub fn mul_nat(a: u128, b: u128) -> u128 {
    a.checked_mul(b).unwrap_or_else(|| overflow("natural multiplication"))
}

#[inline(always)]
pub fn div_nat(a: u128, b: u128) -> u128 {
    if b == 0 { 0 } else { a / b }
}

#[inline(always)]
pub fn rem_nat(a: u128, b: u128) -> u128 {
    if b == 0 { a } else { a % b }
}

#[inline]
pub fn pow_int(mut base: i128, mut exponent: u128) -> i128 {
    let mut result = 1i128;
    while exponent != 0 {
        if exponent & 1 == 1 {
            result = mul_int(result, base);
        }
        exponent >>= 1;
        if exponent != 0 {
            base = mul_int(base, base);
        }
    }
    result
}

#[inline]
pub fn pow_nat(mut base: u128, mut exponent: u128) -> u128 {
    let mut result = 1u128;
    while exponent != 0 {
        if exponent & 1 == 1 {
            result = mul_nat(result, base);
        }
        exponent >>= 1;
        if exponent != 0 {
            base = mul_nat(base, base);
        }
    }
    result
}

#[inline]
pub fn push_bit_int(amount: u128, value: i128) -> i128 {
    match amount {
        0 => value,
        1..=126 => value
            .checked_mul(1i128 << amount as u32)
            .unwrap_or_else(|| overflow("integer left shift")),
        127 if value == -1 => i128::MIN,
        127 if value == 0 => 0,
        _ if value == 0 => 0,
        _ => overflow("integer left shift"),
    }
}

#[inline(always)]
pub fn drop_bit_int(amount: u128, value: i128) -> i128 {
    if amount >= 128 {
        if value < 0 { -1 } else { 0 }
    } else {
        value >> amount as u32
    }
}

#[inline]
pub fn take_bit_int(amount: u128, value: i128) -> i128 {
    if amount >= 128 {
        if value >= 0 { value } else { overflow("integer take_bit") }
    } else if amount == 0 {
        0
    } else {
        value & ((1i128 << amount as u32) - 1)
    }
}

#[inline]
pub fn mask_int(amount: u128) -> i128 {
    if amount > 127 {
        overflow("integer mask")
    } else if amount == 0 {
        0
    } else {
        (1i128 << amount as u32) - 1
    }
}

#[inline]
pub fn set_bit_int(amount: u128, value: i128) -> i128 {
    if amount < 127 {
        value | (1i128 << amount as u32)
    } else if value < 0 {
        value
    } else {
        overflow("integer set_bit")
    }
}

#[inline]
pub fn unset_bit_int(amount: u128, value: i128) -> i128 {
    if amount < 127 {
        value & !(1i128 << amount as u32)
    } else if value >= 0 {
        value
    } else {
        overflow("integer unset_bit")
    }
}

#[inline]
pub fn flip_bit_int(amount: u128, value: i128) -> i128 {
    if amount < 127 {
        value ^ (1i128 << amount as u32)
    } else {
        let _ = value;
        overflow("integer flip_bit")
    }
}

#[inline(always)]
pub fn bit_int(value: i128, amount: u128) -> bool {
    if amount >= 128 { value < 0 } else { ((value >> amount as u32) & 1) == 1 }
}

#[inline]
pub fn push_bit_nat(amount: u128, value: u128) -> u128 {
    if amount >= 128 {
        if value == 0 { 0 } else { overflow("natural left shift") }
    } else {
        value
            .checked_mul(1u128 << amount as u32)
            .unwrap_or_else(|| overflow("natural left shift"))
    }
}

#[inline(always)]
pub fn drop_bit_nat(amount: u128, value: u128) -> u128 {
    if amount >= 128 { 0 } else { value >> amount as u32 }
}

#[inline(always)]
pub fn take_bit_nat(amount: u128, value: u128) -> u128 {
    if amount >= 128 {
        value
    } else if amount == 0 {
        0
    } else {
        value & ((1u128 << amount as u32) - 1)
    }
}

#[inline]
pub fn mask_nat(amount: u128) -> u128 {
    if amount > 128 {
        overflow("natural mask")
    } else if amount == 128 {
        u128::MAX
    } else if amount == 0 {
        0
    } else {
        (1u128 << amount as u32) - 1
    }
}

#[inline]
pub fn set_bit_nat(amount: u128, value: u128) -> u128 {
    if amount >= 128 { overflow("natural set_bit") } else { value | (1u128 << amount as u32) }
}

#[inline(always)]
pub fn unset_bit_nat(amount: u128, value: u128) -> u128 {
    if amount >= 128 { value } else { value & !(1u128 << amount as u32) }
}

#[inline]
pub fn flip_bit_nat(amount: u128, value: u128) -> u128 {
    if amount >= 128 { overflow("natural flip_bit") } else { value ^ (1u128 << amount as u32) }
}

#[inline(always)]
pub fn bit_nat(value: u128, amount: u128) -> bool {
    amount < 128 && ((value >> amount as u32) & 1) == 1
}
\<close>

code_reserved (Rust) Rust_Checked128

code_printing
  type_constructor "integer" \<rightharpoonup> (Rust) "i128"
| type_constructor int \<rightharpoonup> (Rust) "i128"
| type_constructor nat \<rightharpoonup> (Rust) "u128"

code_printing
  constant "0 :: integer" \<rightharpoonup> (Rust) "0i128"
| constant int_of_integer \<rightharpoonup> (Rust) "_"
| constant integer_of_int \<rightharpoonup> (Rust) "_"
| constant Code_Target_Nat.Nat \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::from'_int'(_')"
| constant Code_Numeral.nat_of_integer \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::from'_int'(_')"
| constant integer_of_nat \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::into'_int'(_')"
| constant "0 :: nat" \<rightharpoonup> (Rust) "0u128"

setup \<open>
let
  val min_i128 = ~ (Integer.pow 127 2)
  val max_i128 = Integer.pow 127 2 - 1

  fun print_checked_int _ k =
    if k < min_i128 orelse max_i128 < k then
      error ("Rust_Checked128_Setup: integer literal outside i128: " ^ Int.toString k)
    else if k = min_i128 then
      "i128::MIN"
    else if k < 0 then
      "(-" ^ Int.toString (~ k) ^ "i128)"
    else
      Int.toString k ^ "i128"
in
  Numeral.add_code \<^const_name>\<open>Code_Numeral.Pos\<close> I print_checked_int "Rust"
  #> Numeral.add_code \<^const_name>\<open>Code_Numeral.Neg\<close> (~) print_checked_int "Rust"
end
\<close>

code_printing
  constant "plus :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::add'_int'(_, _')"
| constant "uminus :: integer \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::neg'_int'(_')"
| constant "minus :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::sub'_int'(_, _')"
| constant Code_Numeral.dup \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::duplicate'(_')"
| constant Code_Numeral.sub \<rightharpoonup> (Rust) "panic'!(\"sub\")"
| constant "times :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::mul'_int'(_, _')"
| constant "divide :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::div'_int'(_, _')"
| constant "modulo :: integer \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::rem'_int'(_, _')"
| constant Code_Numeral.divmod_abs \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::divmod'_abs'(_, _')"
| constant "HOL.equal :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "=="
| constant "less_eq :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<="
| constant "less :: integer \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<"
| constant "abs :: integer \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::abs'_int'(_')"
| constant "Bit_Operations.and :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 7 "&"
| constant "Bit_Operations.or :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 5 "|"
| constant "Bit_Operations.xor :: integer \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) infixl 6 "^"
| constant "Bit_Operations.not :: integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "'! _"

code_printing
  constant "plus :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::add'_nat'(_, _')"
| constant "minus :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::sub'_nat'(_, _')"
| constant "times :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::mul'_nat'(_, _')"
| constant "divide :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::div'_nat'(_, _')"
| constant "modulo :: nat \<Rightarrow> _ \<Rightarrow> _" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::rem'_nat'(_, _')"
| constant "HOL.equal :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "=="
| constant "less_eq :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<="
| constant "less :: nat \<Rightarrow> _ \<Rightarrow> bool" \<rightharpoonup>
    (Rust) infix 4 "<"
| constant rust_checked_integer_power \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::pow'_int'(_, _')"
| constant rust_checked_nat_power \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::pow'_nat'(_, _')"
| constant "Bit_Operations.push_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::push'_bit'_int'(_, _')"
| constant "Bit_Operations.drop_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::drop'_bit'_int'(_, _')"
| constant "Bit_Operations.take_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::take'_bit'_int'(_, _')"
| constant "Bit_Operations.mask :: nat \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::mask'_int'(_')"
| constant "Bit_Operations.set_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::set'_bit'_int'(_, _')"
| constant "Bit_Operations.unset_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::unset'_bit'_int'(_, _')"
| constant "Bit_Operations.flip_bit :: nat \<Rightarrow> integer \<Rightarrow> integer" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::flip'_bit'_int'(_, _')"
| constant "Bit_Operations.bit :: integer \<Rightarrow> nat \<Rightarrow> bool" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::bit'_int'(_, _')"
| constant "Bit_Operations.push_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::push'_bit'_nat'(_, _')"
| constant "Bit_Operations.drop_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::drop'_bit'_nat'(_, _')"
| constant "Bit_Operations.take_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::take'_bit'_nat'(_, _')"
| constant "Bit_Operations.mask :: nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::mask'_nat'(_')"
| constant "Bit_Operations.set_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::set'_bit'_nat'(_, _')"
| constant "Bit_Operations.unset_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::unset'_bit'_nat'(_, _')"
| constant "Bit_Operations.flip_bit :: nat \<Rightarrow> nat \<Rightarrow> nat" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::flip'_bit'_nat'(_, _')"
| constant "Bit_Operations.bit :: nat \<Rightarrow> nat \<Rightarrow> bool" \<rightharpoonup>
    (Rust) "!crate::Rust'_Checked128::bit'_nat'(_, _')"

end
