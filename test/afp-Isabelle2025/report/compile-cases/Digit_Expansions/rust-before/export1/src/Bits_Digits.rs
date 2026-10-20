use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::power;
use crate::Euclidean_Rings::divide_nat;
use crate::Euclidean_Rings::modulo_nat;

pub fn nth_bit (num: BigInt, k: BigInt) -> BigInt {
    modulo_nat(divide_nat(num.clone(), power((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), k.clone())), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }))
}

pub fn nth_digit (num: BigInt, k: BigInt, base: BigInt) -> BigInt {
    modulo_nat(divide_nat(num.clone(), power(base.clone(), k.clone())), base.clone())
}
