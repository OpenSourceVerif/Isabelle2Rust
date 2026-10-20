use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::modulo_integer;

pub fn gcd_integer (k: BigInt, l: BigInt) -> BigInt {
    (if l.clone() == BigInt::ZERO {
          k.clone()
      } else {
          gcd_integer(l.clone(), modulo_integer((k.clone().abs()), (l.clone().abs())))
      }.abs())
}

pub fn gcd_int (x0: BigInt, x1: BigInt) -> BigInt {
    match (x0, x1) {
        (x, y) =>
            gcd_integer(x.clone(), y.clone()),
        _ =>
            panic!("non-exhaustive match")
    }
}
