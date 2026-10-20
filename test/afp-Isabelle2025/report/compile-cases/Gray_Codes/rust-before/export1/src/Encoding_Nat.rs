use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::one_nat;
use crate::Arith::suc;
use crate::Euclidean_Rings::divide_nat;
use crate::Euclidean_Rings::modulo_nat;
use crate::HOL::undefined;
use crate::List::List;
use crate::List::size_list;

pub fn enc (uu: BigInt, v: BigInt) -> List<BigInt> {
    if v.clone() == BigInt::ZERO {
        List::Nil
    } else {
        if (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }) <=
             uu.clone() {
            List::Cons (modulo_nat(suc((match (v.clone().clone(), one_nat().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })), uu.clone()), Box::new(enc(uu.clone(), divide_nat(suc((match (v.clone().clone(), one_nat().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })), uu.clone()))))
        } else {
            undefined::<List<BigInt>>()
        }
    }
}

pub fn inc (b: BigInt, x1: List<BigInt>) -> List<BigInt> {
    match (b, x1) {
        (_, List::Nil) =>
            List::Nil,
        (b, List::Cons (a, p0)) =>
            {
                let w = *p0;
                List::Cons (
                    modulo_nat(suc(a.clone()), b.clone()),
                    Box::new(if ! (suc(a.clone()) == b.clone()) {
                          w.clone()
                      } else {
                          inc(b.clone(), w.clone())
                      })
                )
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn vala (b: BigInt, x1: List<BigInt>) -> BigInt {
    match (b, x1) {
        (_, List::Nil) =>
            BigInt::ZERO,
        (b, List::Cons (a, p0)) =>
            {
                let w = *p0;
                a.clone() + b.clone() * vala(b.clone(), w.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn lenc (k: BigInt, uu: BigInt, uv: BigInt) -> List<BigInt> {
    if k.clone() == BigInt::ZERO {
        List::Nil
    } else {
        List::Cons (modulo_nat(uv.clone(), uu.clone()), Box::new(lenc((match (k.clone().clone(), one_nat().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }), uu.clone(), divide_nat(uv.clone(), uu.clone()))))
    }
}

pub fn valid (b: BigInt, x1: List<BigInt>) -> bool {
    match (b, x1) {
        (b, List::Nil) =>
            (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }) <=
              b.clone(),
        (b, List::Cons (a, p0)) =>
            {
                let w = *p0;
                a.clone() < b.clone() && valid(b.clone(), w.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn enc_len (uu: BigInt, v: BigInt) -> BigInt {
    if v.clone() == BigInt::ZERO {
        BigInt::ZERO
    } else {
        if (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }) <=
             uu.clone() {
            suc(enc_len(uu.clone(), divide_nat(suc((match (v.clone().clone(), one_nat().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })), uu.clone())))
        } else {
            undefined::<BigInt>()
        }
    }
}

pub fn normal (b: BigInt, w: List<BigInt>) -> bool {
    enc_len(b.clone(), vala(b.clone(), w.clone())) == size_list(w.clone())
}
