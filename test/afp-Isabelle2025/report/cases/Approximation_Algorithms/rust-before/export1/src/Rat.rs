use num_bigint::*;
use num_traits::sign::Signed as _;

#[derive(Clone)]
pub enum Rat {
    Frct ((BigInt, BigInt))
}
