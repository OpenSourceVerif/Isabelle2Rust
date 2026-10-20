use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::divide_integer;
use crate::Arith::modulo_integer;

pub fn divide_int (k: BigInt, l: BigInt) -> BigInt {
    divide_integer(k.clone(), l.clone())
}

pub fn divide_nat (m: BigInt, n: BigInt) -> BigInt {
    divide_integer(m.clone(), n.clone())
}

pub fn modulo_nat (m: BigInt, n: BigInt) -> BigInt {
    modulo_integer(m.clone(), n.clone())
}
