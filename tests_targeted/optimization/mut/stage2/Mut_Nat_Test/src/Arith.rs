use num_bigint::*;
use num_traits::sign::*;
#[derive(Clone)]
pub enum Num {
    One,
    Bit0(Box<Num>),
    Bit1(Box<Num>),
}

pub fn one_nat() -> BigInt {
    BigInt::from_bytes_be(Sign::Plus, &vec!(1))
}

