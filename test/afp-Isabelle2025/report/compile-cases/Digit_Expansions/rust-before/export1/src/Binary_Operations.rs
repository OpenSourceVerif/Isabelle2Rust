use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::One;
use crate::Arith::suc;
use crate::Euclidean_Rings::divide_nat;
use crate::Euclidean_Rings::modulo_nat;

pub fn masks (v: BigInt, uu: BigInt) -> bool {
    if v.clone() == BigInt::ZERO {
        true
    } else {
        masks(divide_nat(suc((match (v.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), divide_nat(uu.clone(), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }))) &&
          modulo_nat(suc((match (v.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })) <=
            modulo_nat(uu.clone(), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }))
    }
}

pub fn bitand_nat (v: BigInt, uu: BigInt) -> BigInt {
    if v.clone() == BigInt::ZERO {
        BigInt::ZERO
    } else {
        (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }) *
          bitand_nat(divide_nat(suc((match (v.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), divide_nat(uu.clone(), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }))) +
          modulo_nat(suc((match (v.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })) *
            modulo_nat(uu.clone(), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }))
    }
}

pub fn orthogonal (a: BigInt, b: BigInt) -> bool {
    bitand_nat(a.clone(), b.clone()) == BigInt::ZERO
}
