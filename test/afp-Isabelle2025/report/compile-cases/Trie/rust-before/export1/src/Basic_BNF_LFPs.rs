use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::suc;

use std::rc::Rc;

pub fn size_prod <B, A>
    (xa: Rc<dyn Fn(A) -> BigInt>, x: Rc<dyn Fn(B) -> BigInt>,
      xb2: (A, B)) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (xa, x, xb2) {
        (xa, x, (x1, x2)) =>
            (*xa)(x1.clone()) + (*x)(x2.clone()) + suc(BigInt::ZERO),
        _ =>
            panic!("non-exhaustive match")
    }
}
