use num_bigint::*;

use num_traits::sign::Signed as _;

#[derive(Clone)]
pub enum Num {
    One,
    Bit0(Box<Num>),
    Bit1(Box<Num>),
}

pub fn one_nat() -> BigInt {
    BigInt::from_bytes_be(Sign::Plus, &[1])
}

// borrow-optimized by shared parameters
pub fn suc(n: &BigInt) -> BigInt {
    n.clone() + one_nat()
}

