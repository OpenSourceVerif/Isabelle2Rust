use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Minus;
use crate::Arith::One;
use crate::Arith::Plus;
use crate::Arith::Sgn;
use crate::Arith::Times;
use crate::Arith::Uminus;
use crate::Arith::Zero;
use crate::Arith::abs_int;
use crate::Arith::less_int;
use crate::GCD::Gcda;
use crate::HOL::Equal;
use crate::Product_Type::fst;
use crate::Product_Type::snd;
use crate::Rings::Divide;

#[derive(Clone)]
pub enum Rat {
    Frct ((BigInt, BigInt))
}

pub fn normalize (p: (BigInt, BigInt)) -> (BigInt, BigInt) {
    if less_int(<BigInt as Zero>::zero(), snd(p.clone())) {
        {
            let a = <BigInt as Gcda>::gcda(fst(p.clone()), snd(p.clone()));
            (<BigInt as Divide>::divide(fst(p.clone()), a.clone()), <BigInt as Divide>::divide(snd(p.clone()), a.clone()))
        }
    } else {
        if <BigInt as Equal>::equal(snd(p.clone()), <BigInt as Zero>::zero()) {
            (<BigInt as Zero>::zero(), <BigInt as One>::one())
        } else {
            {
                let a = <BigInt as Uminus>::uminus(<BigInt as Gcda>::gcda(fst(p.clone()), snd(p.clone())));
                (<BigInt as Divide>::divide(fst(p.clone()), a.clone()), <BigInt as Divide>::divide(snd(p.clone()), a.clone()))
            }
        }
    }
}

pub fn quotient_of (x0: Rat) -> (BigInt, BigInt) {
    let Rat::Frct (x) = x0;
    x.clone()
}

impl One for Rat {
    fn one () -> Rat {
        Rat::Frct ((<BigInt as One>::one(), <BigInt as One>::one()))
    }
}

pub fn less_rat (p: Rat, q: Rat) -> bool {
    match quotient_of(p.clone()) {
        (a, c) =>
            match quotient_of(q.clone()) {
                (b, d) =>
                    less_int(<BigInt as Times>::times(a.clone(), d.clone()), <BigInt as Times>::times(c.clone(), b.clone())),
                _ =>
                    panic!("non-exhaustive match")
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

impl Plus for Rat {
    fn plus (p: Rat, q: Rat) -> Rat {
        Rat::Frct (
            match quotient_of(p.clone()) {
                (a, c) =>
                    match quotient_of(q.clone()) {
                        (b, d) =>
                            normalize((<BigInt as Plus>::plus(<BigInt as Times>::times(a.clone(), d.clone()), <BigInt as Times>::times(b.clone(), c.clone())), <BigInt as Times>::times(c.clone(), d.clone()))),
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

impl Equal for Rat {
    fn equal (a: Rat, b: Rat) -> bool {
        <(BigInt, BigInt) as Equal>::equal(quotient_of(a.clone()), quotient_of(b.clone()))
    }
}

impl Minus for Rat {
    fn minus (p: Rat, q: Rat) -> Rat {
        Rat::Frct (
            match quotient_of(p.clone()) {
                (a, c) =>
                    match quotient_of(q.clone()) {
                        (b, d) =>
                            normalize((<BigInt as Minus>::minus(<BigInt as Times>::times(a.clone(), d.clone()), <BigInt as Times>::times(b.clone(), c.clone())), <BigInt as Times>::times(c.clone(), d.clone()))),
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        )
    }
}

impl Times for Rat {
    fn times (p: Rat, q: Rat) -> Rat {
        Rat::Frct (
            match quotient_of(p.clone()) {
                (a, c) =>
                    match quotient_of(q.clone()) {
                        (b, d) =>
                            normalize((<BigInt as Times>::times(a.clone(), b.clone()), <BigInt as Times>::times(c.clone(), d.clone()))),
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        )
    }
}

impl Divide for Rat {
    fn divide (p: Rat, q: Rat) -> Rat {
        Rat::Frct (
            match quotient_of(p.clone()) {
                (a, c) =>
                    match quotient_of(q.clone()) {
                        (b, d) =>
                            normalize((<BigInt as Times>::times(a.clone(), d.clone()), <BigInt as Times>::times(c.clone(), b.clone()))),
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        )
    }
}

impl Uminus for Rat {
    fn uminus (p: Rat) -> Rat {
        Rat::Frct (
            match quotient_of(p.clone()) {
                (a, b) =>
                    (<BigInt as Uminus>::uminus(a.clone()), b.clone()),
                _ =>
                    panic!("non-exhaustive match")
            }
        )
    }
}

impl crate::Fields::Inverse for Rat {
    fn inverse (p: Rat) -> Rat {
        Rat::Frct (
            match quotient_of(p.clone()) {
                (a, b) =>
                    if <BigInt as Equal>::equal(a.clone(), <BigInt as Zero>::zero()) {
                        (<BigInt as Zero>::zero(), <BigInt as One>::one())
                    } else {
                        (<BigInt as Times>::times(<BigInt as Sgn>::sgn(a.clone()), b.clone()), abs_int(a.clone()))
                    },
                _ =>
                    panic!("non-exhaustive match")
            }
        )
    }
}
