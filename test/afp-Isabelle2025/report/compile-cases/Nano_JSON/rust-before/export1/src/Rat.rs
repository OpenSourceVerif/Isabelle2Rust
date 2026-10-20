use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::less_int;
use crate::Arith::one_int;
use crate::Arith::times_int;
use crate::Arith::uminus_int;
use crate::Arith::zero_int;
use crate::Euclidean_Rings::divide_int;
use crate::GCD::gcd_int;
use crate::HOL::Equal;
use crate::Product_Type::fst;
use crate::Product_Type::snd;

#[derive(Clone)]
pub enum Rat {
    Frct ((BigInt, BigInt))
}

pub fn of_int (a: BigInt) -> Rat {
    Rat::Frct ((a.clone(), one_int()))
}

pub fn normalize (p: (BigInt, BigInt)) -> (BigInt, BigInt) {
    if less_int(zero_int(), snd(p.clone())) {
        {
            let a = gcd_int(fst(p.clone()), snd(p.clone()));
            (divide_int(fst(p.clone()), a.clone()), divide_int(snd(p.clone()), a.clone()))
        }
    } else {
        if <BigInt as Equal>::equal(snd(p.clone()), zero_int()) {
            (zero_int(), one_int())
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

pub fn divide_rat (p: Rat, q: Rat) -> Rat {
    Rat::Frct (
        match quotient_of(p.clone()) {
            (a, c) =>
                match quotient_of(q.clone()) {
                    (b, d) =>
                        normalize((times_int(a.clone(), d.clone()), times_int(c.clone(), b.clone()))),
                    _ =>
                        panic!("non-exhaustive match")
                },
            _ =>
                panic!("non-exhaustive match")
        }
    )
}

pub fn uminus_rat (p: Rat) -> Rat {
    Rat::Frct (
        match quotient_of(p.clone()) {
            (a, b) =>
                (uminus_int(a.clone()), b.clone()),
            _ =>
                panic!("non-exhaustive match")
        }
    )
}
