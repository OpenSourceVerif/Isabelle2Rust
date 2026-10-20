use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::One;
use crate::Arith::power;
use crate::Euclidean_Rings::divide_nat;
use crate::Euclidean_Rings::modulo_nat;

pub fn bin_carry (a: BigInt, b: BigInt, k: BigInt) -> BigInt {
    divide_nat(modulo_nat(a.clone(), power((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), k.clone())) +
                 modulo_nat(b.clone(), power((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), k.clone())), power((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), k.clone()))
}

pub fn bin_narry (a: BigInt, b: BigInt, k: BigInt) -> BigInt {
    if modulo_nat(a.clone(), power((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), k.clone())) <
         modulo_nat(b.clone(), power((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), k.clone())) {
        <BigInt as One>::one()
    } else {
        BigInt::ZERO
    }
}

pub fn bin_narry2 (a: BigInt, b: BigInt, k: BigInt) -> BigInt {
    modulo_nat(divide_nat((match ((power((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), k.clone()) +
                                    modulo_nat(a.clone(), power((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), k.clone()))).clone(), modulo_nat(b.clone(), power((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), k.clone())).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }), power((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), k.clone())) +
                 <BigInt as One>::one(), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }))
}
