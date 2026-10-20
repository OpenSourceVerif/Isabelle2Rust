use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::one_nat;
use crate::List::List;

pub fn dist1 (b: BigInt, x: BigInt, y: BigInt) -> BigInt {
    if x.clone() <= y.clone() {
        (match (y.clone().clone(), x.clone().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
    } else {
        (match ((b.clone() +
                  y.clone()).clone(), x.clone().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
    }
}

pub fn dist (b: BigInt, x1: List<BigInt>, x2: List<BigInt>) -> BigInt {
    match (b, x1, x2) {
        (_, List::Nil, List::Nil) =>
            BigInt::ZERO,
        (b, List::Cons (x, p0), List::Nil) =>
            {
                let xs = *p0;
                dist1(b.clone(), x.clone(), BigInt::ZERO) +
                  dist(b.clone(), xs.clone(), List::Nil)
            },
        (b, List::Nil, List::Cons (y, p0)) =>
            {
                let ys = *p0;
                dist1(b.clone(), BigInt::ZERO, y.clone()) +
                  dist(b.clone(), List::Nil, ys.clone())
            },
        (b, List::Cons (x, p0), List::Cons (y, p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                dist1(b.clone(), x.clone(), y.clone()) +
                  dist(b.clone(), xs.clone(), ys.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn hamming (x0: List<BigInt>, x1: List<BigInt>) -> BigInt {
    match (x0, x1) {
        (List::Nil, List::Nil) =>
            BigInt::ZERO,
        (List::Cons (a, p0), List::Cons (b, p1)) =>
            {
                let v = *p0;
                let w = *p1;
                if ! (a.clone() == b.clone()) {
                      one_nat()
                  } else {
                      BigInt::ZERO
                  } + hamming(v.clone(), w.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}
