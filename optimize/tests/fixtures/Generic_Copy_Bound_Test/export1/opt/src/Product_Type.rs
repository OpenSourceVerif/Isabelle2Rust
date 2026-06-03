use num_bigint::*;
use num_traits::sign::*;
#[derive(Clone, Copy)]
pub enum Prod <A, B> {
    Pair(A, B),
}

