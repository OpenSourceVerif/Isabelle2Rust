use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Code_Word_Dist::dist1;
use crate::Euclidean_Rings::modulo_nat;
use crate::Groups_List::sum_list;
use crate::List::List;

pub fn decode (b: BigInt, x1: List<BigInt>) -> List<BigInt> {
    match (b, x1) {
        (_, List::Nil) =>
            List::Nil,
        (b, List::Cons (g, p0)) =>
            {
                let c = *p0;
                List::Cons (modulo_nat(g.clone() +
 modulo_nat(sum_list(c.clone()), b.clone()), b.clone()), Box::new(decode(b.clone(), c.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn to_gray (b: BigInt, x1: List<BigInt>) -> List<BigInt> {
    match (b, x1) {
        (_, List::Nil) =>
            List::Nil,
        (b, List::Cons (a, p0)) =>
            {
                let v = *p0;
                {
                    let g = to_gray(b.clone(), v.clone());
                    List::Cons (dist1(b.clone(), modulo_nat(sum_list(g.clone()), b.clone()), a.clone()), Box::new(g.clone()))
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}
