use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::HOL::Equal;
use crate::Orderings::Ord;
use crate::Orderings::max;
use crate::Product_Type::apsnd;
use crate::Product_Type::fst;
use crate::Product_Type::snd;

use std::rc::Rc;

#[derive(Clone)]
pub enum Natural {
    Nat (BigInt)
}

pub fn integer_of_natural (x0: Natural) -> BigInt {
    let Natural::Nat (x) = x0;
    x.clone()
}

impl Plus for Natural {
    fn plus (m: Natural, n: Natural) -> Natural {
        Natural::Nat (integer_of_natural(m.clone()) +
                        integer_of_natural(n.clone()))
    }
}

pub trait Plus {
    fn plus (x0: Self, x1: Self) -> Self where Self: Sized;
}

impl Zero for Natural {
    fn zero () -> Natural {
        Natural::Nat (BigInt::ZERO)
    }
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

pub fn natural_of_integer (k: BigInt) -> Natural {
    Natural::Nat (max(BigInt::ZERO, k.clone()))
}

pub fn one_natural () -> Natural {
    Natural::Nat (BigInt::from_bytes_be(Sign::Plus, &[1]))
}

impl Equal for Natural {
    fn equal (m: Natural, n: Natural) -> bool {
        integer_of_natural(m.clone()) == integer_of_natural(n.clone())
    }
}

pub fn minus_natural (m: Natural, n: Natural) -> Natural {
    Natural::Nat (max(BigInt::ZERO, integer_of_natural(m.clone()) -
                                      integer_of_natural(n.clone())))
}

impl Ord for Natural {
    fn less_eq (m: Natural, n: Natural) -> bool {
        integer_of_natural(m.clone()) <= integer_of_natural(n.clone())
    }
    fn less (m: Natural, n: Natural) -> bool {
        integer_of_natural(m.clone()) < integer_of_natural(n.clone())
    }
}

pub fn times_natural (m: Natural, n: Natural) -> Natural {
    Natural::Nat (integer_of_natural(m.clone()) * integer_of_natural(n.clone()))
}

pub fn divide_integer (k: BigInt, l: BigInt) -> BigInt {
    fst(divmod_integer(k.clone(), l.clone()))
}

pub fn divide_natural (m: Natural, n: Natural) -> Natural {
    Natural::Nat (divide_integer(integer_of_natural(m.clone()), integer_of_natural(n.clone())))
}

pub fn modulo_integer (k: BigInt, l: BigInt) -> BigInt {
    snd(divmod_integer(k.clone(), l.clone()))
}

pub fn modulo_natural (m: Natural, n: Natural) -> Natural {
    Natural::Nat (modulo_integer(integer_of_natural(m.clone()), integer_of_natural(n.clone())))
}
