use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::divide_integer;

pub fn divide_nat (m: BigInt, n: BigInt) -> BigInt {
    divide_integer(m.clone(), n.clone())
}
