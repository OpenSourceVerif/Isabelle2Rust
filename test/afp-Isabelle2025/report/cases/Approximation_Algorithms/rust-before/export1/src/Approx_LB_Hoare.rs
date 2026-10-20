use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::One;
use crate::Arith::suc;
use crate::Orderings::max;

use std::rc::Rc;

pub fn f__max_0 (f: Rc<dyn Fn(BigInt) -> BigInt>, x: BigInt) -> BigInt {
    if x.clone() == BigInt::ZERO {
        BigInt::ZERO
    } else {
        max((*f)(suc((match (x.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }))), f__max_0(f.clone(), (match (x.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })))
    }
}
