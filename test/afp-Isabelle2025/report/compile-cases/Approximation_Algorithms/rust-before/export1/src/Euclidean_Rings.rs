use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Product_Type::map_prod;

use std::rc::Rc;

pub fn divmod_nat (m: BigInt, n: BigInt) -> (BigInt, BigInt) {
    let k = m.clone();
    let l = n.clone();
    map_prod(
        ((Rc::new(move |a: BigInt| -> BigInt {
            (match a.clone().clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })
        })) as Rc<dyn Fn(BigInt) -> BigInt>),
        ((Rc::new(move |a: BigInt| -> BigInt {
            (match a.clone().clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })
        })) as Rc<dyn Fn(BigInt) -> BigInt>),
        if k.clone() == BigInt::ZERO {
            (BigInt::ZERO, BigInt::ZERO)
        } else {
            if l.clone() == BigInt::ZERO {
                (BigInt::ZERO, k.clone())
            } else {
                std::convert::identity::<(BigInt, BigInt)>((match (k.clone().clone(), l.clone().clone()) { (k, l) => { let k = k.abs(); let l = l.abs(); if l == BigInt::ZERO { (BigInt::ZERO, k) } else { let q = k.clone() / l.clone(); let r = k % l; (q, r) } } }))
            }
        }
    )
}
