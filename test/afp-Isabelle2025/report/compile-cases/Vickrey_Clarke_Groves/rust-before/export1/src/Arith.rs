use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Fun::comp;
use crate::Fun::id;
use crate::HOL::Equal;
use crate::Orderings::Linorder;
use crate::Orderings::Ord;
use crate::Orderings::Order;
use crate::Orderings::Preorder;
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

pub trait AbSemigroupAdd : SemigroupAdd {
    
}

impl<T : SemigroupAdd> AbSemigroupAdd for T {}

pub trait CommMonoidAdd : AbSemigroupAdd + MonoidAdd {
    
}

impl<T : AbSemigroupAdd + MonoidAdd> CommMonoidAdd for T {}

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

pub trait Numeral : One + SemigroupAdd {
    
}

impl<T : One + SemigroupAdd> Numeral for T {}

pub trait Minus {
    fn minus (x0: Self, x1: Self) -> Self where Self: Sized;
}

pub fn suc (n: BigInt) -> BigInt {
    n.clone() + <BigInt as One>::one()
}

pub fn funpow <A> (n: BigInt, f: Rc<dyn Fn(A) -> A>) -> Rc<dyn Fn(A) -> A>
where
    A : Clone + 'static
{
    if n.clone() == BigInt::ZERO {
        ((Rc::new(move |a: A| -> A {
            id(a.clone())
        })) as Rc<dyn Fn(A) -> A>)
    } else {
        (({
            let n_cap = n.clone();
            let f_cap = f.clone();
            Rc::new(move |a: A| -> A {
                (*comp(f_cap.clone(), (({
                    let f_capa = f_cap.clone();
                    let n_capa = n_cap.clone();
                    Rc::new(move |aa: A| -> A {
                        (*funpow((match (n_capa.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }), f_capa.clone()))(aa.clone())
                    })
                }) as Rc<dyn Fn(A) -> A>)))(a.clone())
            })
        }) as Rc<dyn Fn(A) -> A>)
    }
}

pub fn numeral <A> (x0: Num) -> A
where
    A : Clone + Numeral + 'static
{
    match x0 {
        Num::Bit1 (p0) =>
            {
                let n = *p0;
                {
                    let m = numeral::<A>(n.clone());
                    <A as Plus>::plus(<A as Plus>::plus(m.clone(), m.clone()), <A as One>::one())
                }
            },
        Num::Bit0 (p0) =>
            {
                let n = *p0;
                {
                    let m = numeral::<A>(n.clone());
                    <A as Plus>::plus(m.clone(), m.clone())
                }
            },
        Num::One =>
            <A as One>::one(),
        _ =>
            panic!("non-exhaustive match")
    }
}

impl Plus for BigInt {
    fn plus (k: BigInt, l: BigInt) -> BigInt {
        (k.clone() + l.clone())
    }
}

impl Zero for BigInt {
    fn zero () -> BigInt {
        BigInt::ZERO
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

impl Equal for BigInt {
    fn equal (k: BigInt, l: BigInt) -> bool {
        k.clone() == l.clone()
    }
}

impl Minus for BigInt {
    fn minus (k: BigInt, l: BigInt) -> BigInt {
        (k.clone() - l.clone())
    }
}

impl Ord for BigInt {
    fn less_eq (k: BigInt, l: BigInt) -> bool {
        k.clone() <= l.clone()
    }
    fn less (k: BigInt, l: BigInt) -> bool {
        k.clone() < l.clone()
    }
}

pub fn times_int (k: BigInt, l: BigInt) -> BigInt {
    (k.clone() * l.clone())
}

pub fn uminus_int (k: BigInt) -> BigInt {
    (- k.clone())
}

pub fn divide_integer (k: BigInt, l: BigInt) -> BigInt {
    fst(divmod_integer(k.clone(), l.clone()))
}

pub fn modulo_integer (k: BigInt, l: BigInt) -> BigInt {
    snd(divmod_integer(k.clone(), l.clone()))
}
