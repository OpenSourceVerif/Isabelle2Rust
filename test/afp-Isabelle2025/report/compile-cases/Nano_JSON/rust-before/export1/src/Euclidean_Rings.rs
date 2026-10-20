use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::divide_integer;

pub fn divide_int (k: BigInt, l: BigInt) -> BigInt {
    divide_integer(k.clone(), l.clone())
}
