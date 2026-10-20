use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::HOL::Equal;
use crate::Product_Type::apsnd;
use crate::Product_Type::fst;
use crate::Product_Type::snd;
use crate::Rings::CommSemiring;
use crate::Rings::CommSemiring0;
use crate::Rings::CommSemiring0Cancel;
use crate::Rings::CommSemiring1;
use crate::Rings::CommSemiring1Cancel;
use crate::Rings::Dvd;
use crate::Rings::MultZero;
use crate::Rings::Semidom;
use crate::Rings::Semiring;
use crate::Rings::Semiring0;
use crate::Rings::Semiring0Cancel;
use crate::Rings::Semiring1;
use crate::Rings::Semiring1Cancel;
use crate::Rings::Semiring1NoZeroDivisors;
use crate::Rings::SemiringNoZeroDivisors;
use crate::Rings::ZeroNeqOne;

use std::rc::Rc;

impl Equal for BigInt {
    fn equal (k: BigInt, l: BigInt) -> bool {
        k.clone() == l.clone()
    }
}

pub trait Times {
    fn times (x0: Self, x1: Self) -> Self where Self: Sized;
}

#[derive(Clone)]
pub enum Num {
    One,
    Bit0 (Box<Num>),
    Bit1 (Box<Num>)
}

impl One for BigInt {
    fn one () -> BigInt {
        BigInt::from_bytes_be(Sign::Plus, &[1])
    }
}

pub trait One {
    fn one () -> Self where Self: Sized;
}

pub trait Plus {
    fn plus (x0: Self, x1: Self) -> Self where Self: Sized;
}

pub trait Zero {
    fn zero () -> Self where Self: Sized;
}

pub trait SemigroupAdd : Plus {
    
}

impl<T : Plus> SemigroupAdd for T {}

pub trait Numeral : One + SemigroupAdd {
    
}

impl<T : One + SemigroupAdd> Numeral for T {}

pub trait Power : One + Times {
    
}

impl<T : One + Times> Power for T {}

pub trait Minus {
    fn minus (x0: Self, x1: Self) -> Self where Self: Sized;
}

pub trait AbSemigroupAdd : SemigroupAdd {
    
}

impl<T : SemigroupAdd> AbSemigroupAdd for T {}

pub trait MonoidAdd : SemigroupAdd + Zero {
    
}

impl<T : SemigroupAdd + Zero> MonoidAdd for T {}

pub trait CommMonoidAdd : AbSemigroupAdd + MonoidAdd {
    
}

impl<T : AbSemigroupAdd + MonoidAdd> CommMonoidAdd for T {}

pub trait SemigroupMult : Times {
    
}

impl<T : Times> SemigroupMult for T {}

pub trait MonoidMult : SemigroupMult + Power {
    
}

impl<T : SemigroupMult + Power> MonoidMult for T {}

pub trait SemiringNumeral : MonoidMult + Numeral + Semiring {
    
}

impl<T : MonoidMult + Numeral + Semiring> SemiringNumeral for T {}

pub trait CancelSemigroupAdd : SemigroupAdd {
    
}

impl<T : SemigroupAdd> CancelSemigroupAdd for T {}

pub trait CancelAbSemigroupAdd : AbSemigroupAdd + CancelSemigroupAdd + Minus {
    
}

impl<T : AbSemigroupAdd + CancelSemigroupAdd +
        Minus> CancelAbSemigroupAdd for T {}

pub trait CancelCommMonoidAdd : CancelAbSemigroupAdd + CommMonoidAdd {
    
}

impl<T : CancelAbSemigroupAdd + CommMonoidAdd> CancelCommMonoidAdd for T {}

pub trait AbSemigroupMult : SemigroupMult {
    
}

impl<T : SemigroupMult> AbSemigroupMult for T {}

pub trait CommMonoidMult : AbSemigroupMult + MonoidMult + Dvd {
    
}

impl<T : AbSemigroupMult + MonoidMult + Dvd> CommMonoidMult for T {}

pub trait Uminus {
    fn uminus (x0: Self) -> Self where Self: Sized;
}

pub trait GroupAdd : CancelSemigroupAdd + Minus + MonoidAdd + Uminus {
    
}

impl<T : CancelSemigroupAdd + Minus + MonoidAdd + Uminus> GroupAdd for T {}

pub trait NegNumeral : GroupAdd + Numeral {
    
}

impl<T : GroupAdd + Numeral> NegNumeral for T {}

pub trait AbGroupAdd : CancelCommMonoidAdd + GroupAdd {
    
}

impl<T : CancelCommMonoidAdd + GroupAdd> AbGroupAdd for T {}

pub trait Sgn {
    fn sgn (x0: Self) -> Self where Self: Sized;
}

pub fn suc (n: BigInt) -> BigInt {
    n.clone() + <BigInt as One>::one()
}

impl Uminus for BigInt {
    fn uminus (k: BigInt) -> BigInt {
        (- k.clone())
    }
}

impl Zero for BigInt {
    fn zero () -> BigInt {
        BigInt::ZERO
    }
}

pub fn less_int (k: BigInt, l: BigInt) -> bool {
    k.clone() < l.clone()
}

pub fn abs_int (i: BigInt) -> BigInt {
    if less_int(i.clone(), <BigInt as Zero>::zero()) {
        <BigInt as Uminus>::uminus(i.clone())
    } else {
        i.clone()
    }
}

impl Sgn for BigInt {
    fn sgn (i: BigInt) -> BigInt {
        if <BigInt as Equal>::equal(i.clone(), <BigInt as Zero>::zero()) {
            <BigInt as Zero>::zero()
        } else {
            if less_int(<BigInt as Zero>::zero(), i.clone()) {
                <BigInt as One>::one()
            } else {
                <BigInt as Uminus>::uminus(<BigInt as One>::one())
            }
        }
    }
}

impl Plus for BigInt {
    fn plus (k: BigInt, l: BigInt) -> BigInt {
        (k.clone() + l.clone())
    }
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

impl Minus for BigInt {
    fn minus (k: BigInt, l: BigInt) -> BigInt {
        (k.clone() - l.clone())
    }
}

impl Times for BigInt {
    fn times (k: BigInt, l: BigInt) -> BigInt {
        (k.clone() * l.clone())
    }
}

impl crate::Rings::Divide for BigInt {
    fn divide (k: BigInt, l: BigInt) -> BigInt {
        fst(divmod_integer(k.clone(), l.clone()))
    }
}

impl crate::Rings::Modulo for BigInt {
    fn modulo (k: BigInt, l: BigInt) -> BigInt {
        snd(divmod_integer(k.clone(), l.clone()))
    }
}
