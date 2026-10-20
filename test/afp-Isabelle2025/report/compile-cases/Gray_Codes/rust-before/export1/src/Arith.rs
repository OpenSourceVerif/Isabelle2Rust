use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Product_Type::apsnd;
use crate::Product_Type::fst;
use crate::Product_Type::snd;

use std::rc::Rc;

pub trait Plus {
    fn plus (x0: Self, x1: Self) -> Self where Self: Sized;
}

pub trait Zero {
    fn zero () -> Self where Self: Sized;
}

pub trait SemigroupAdd : Plus {
    
}

impl<T : Plus> SemigroupAdd for T {}

pub trait MonoidAdd : SemigroupAdd + Zero {
    
}

impl<T : SemigroupAdd + Zero> MonoidAdd for T {}

#[derive(Clone)]
pub enum Num {
    One,
    Bit0 (Box<Num>),
    Bit1 (Box<Num>)
}

pub fn one_nat () -> BigInt {
    BigInt::from_bytes_be(Sign::Plus, &[1])
}

pub fn suc (n: BigInt) -> BigInt {
    n.clone() + one_nat()
}

pub fn divmod_integer (k: BigInt, l: BigInt) -> (BigInt, BigInt) {
    if k.clone() == BigInt::ZERO {
        (BigInt::ZERO, BigInt::ZERO)
    } else {
        if BigInt::ZERO < l.clone() {
            if BigInt::ZERO < k.clone() {
                std::convert::identity::<(BigInt, BigInt)>((match (k.clone().clone(), l.clone().clone()) { (k, l) => { let k = k.abs(); let l = l.abs(); if l == BigInt::ZERO { (BigInt::ZERO, k) } else { let q = k.clone() / l.clone(); let r = k % l; (q, r) } } }))
            } else {
                match std::convert::identity::<(BigInt, BigInt)>((match (k.clone().clone(), l.clone().clone()) { (k, l) => { let k = k.abs(); let l = l.abs(); if l == BigInt::ZERO { (BigInt::ZERO, k) } else { let q = k.clone() / l.clone(); let r = k % l; (q, r) } } })) {
                    (r, s) =>
                        if s.clone() == BigInt::ZERO {
                            ((- r.clone()), BigInt::ZERO)
                        } else {
                            ((- r.clone()) -
                               BigInt::from_bytes_be(Sign::Plus, &[1]), l.clone() -
                                  s.clone())
                        },
                    _ =>
                        panic!("non-exhaustive match")
                }
            }
        } else {
            if l.clone() == BigInt::ZERO {
                (BigInt::ZERO, k.clone())
            } else {
                apsnd(
                    ((Rc::new(move |a: BigInt| -> BigInt {
                        (- a.clone())
                    })) as Rc<dyn Fn(BigInt) -> BigInt>),
                    if k.clone() < BigInt::ZERO {
                        std::convert::identity::<(BigInt, BigInt)>((match (k.clone().clone(), l.clone().clone()) { (k, l) => { let k = k.abs(); let l = l.abs(); if l == BigInt::ZERO { (BigInt::ZERO, k) } else { let q = k.clone() / l.clone(); let r = k % l; (q, r) } } }))
                    } else {
                        match std::convert::identity::<(BigInt, BigInt)>((match (k.clone().clone(), l.clone().clone()) { (k, l) => { let k = k.abs(); let l = l.abs(); if l == BigInt::ZERO { (BigInt::ZERO, k) } else { let q = k.clone() / l.clone(); let r = k % l; (q, r) } } })) {
                            (r, s) =>
                                if s.clone() == BigInt::ZERO {
                                    ((- r.clone()), BigInt::ZERO)
                                } else {
                                    ((- r.clone()) -
                                       BigInt::from_bytes_be(Sign::Plus, &[1]), (- l.clone()) -
  s.clone())
                                },
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    }
                )
            }
        }
    }
}

pub fn divide_integer (k: BigInt, l: BigInt) -> BigInt {
    fst(divmod_integer(k.clone(), l.clone()))
}

pub fn modulo_integer (k: BigInt, l: BigInt) -> BigInt {
    snd(divmod_integer(k.clone(), l.clone()))
}
