use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Minus;
use crate::Arith::One;
use crate::Arith::Plus;
use crate::Arith::Zero;
use crate::Arith::times_int;
use crate::Arith::uminus_int;
use crate::Euclidean_Rings::divide_int;
use crate::GCD::gcd_int;
use crate::HOL::Equal;
use crate::Orderings::Ord;
use crate::Product_Type::fst;
use crate::Product_Type::snd;

#[derive(Clone)]
pub enum Rat {
    Frct ((BigInt, BigInt))
}

pub fn normalize (p: (BigInt, BigInt)) -> (BigInt, BigInt) {
    if <BigInt as Ord>::less(<BigInt as Zero>::zero(), snd(p.clone())) {
        {
            let a = gcd_int(fst(p.clone()), snd(p.clone()));
            (divide_int(fst(p.clone()), a.clone()), divide_int(snd(p.clone()), a.clone()))
        }
    } else {
        if <BigInt as Equal>::equal(snd(p.clone()), <BigInt as Zero>::zero()) {
            (<BigInt as Zero>::zero(), <BigInt as One>::one())
        } else {
            {
                let a = uminus_int(gcd_int(fst(p.clone()), snd(p.clone())));
                (divide_int(fst(p.clone()), a.clone()), divide_int(snd(p.clone()), a.clone()))
            }
        }
    }
}

pub fn quotient_of (x0: Rat) -> (BigInt, BigInt) {
    let Rat::Frct (x) = x0;
    x.clone()
}

impl Plus for Rat {
    fn plus (p: Rat, q: Rat) -> Rat {
        Rat::Frct (
            match quotient_of(p.clone()) {
                (a, c) =>
                    match quotient_of(q.clone()) {
                        (b, d) =>
                            normalize((<BigInt as Plus>::plus(times_int(a.clone(), d.clone()), times_int(b.clone(), c.clone())), times_int(c.clone(), d.clone()))),
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        )
    }
}

impl Zero for Rat {
    fn zero () -> Rat {
        Rat::Frct ((<BigInt as Zero>::zero(), <BigInt as One>::one()))
    }
}

impl Minus for Rat {
    fn minus (p: Rat, q: Rat) -> Rat {
        Rat::Frct (
            match quotient_of(p.clone()) {
                (a, c) =>
                    match quotient_of(q.clone()) {
                        (b, d) =>
                            normalize((<BigInt as Minus>::minus(times_int(a.clone(), d.clone()), times_int(b.clone(), c.clone())), times_int(c.clone(), d.clone()))),
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        )
    }
}

impl Ord for Rat {
    fn less_eq (p: Rat, q: Rat) -> bool {
        match quotient_of(p.clone()) {
            (a, c) =>
                match quotient_of(q.clone()) {
                    (b, d) =>
                        <BigInt as Ord>::less_eq(times_int(a.clone(), d.clone()), times_int(c.clone(), b.clone())),
                    _ =>
                        panic!("non-exhaustive match")
                },
            _ =>
                panic!("non-exhaustive match")
        }
    }
    fn less (p: Rat, q: Rat) -> bool {
        match quotient_of(p.clone()) {
            (a, c) =>
                match quotient_of(q.clone()) {
                    (b, d) =>
                        <BigInt as Ord>::less(times_int(a.clone(), d.clone()), times_int(c.clone(), b.clone())),
                    _ =>
                        panic!("non-exhaustive match")
                },
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
