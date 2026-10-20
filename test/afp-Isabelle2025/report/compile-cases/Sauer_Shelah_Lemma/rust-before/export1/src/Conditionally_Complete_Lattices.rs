use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::HOL::Equal;
use crate::Lattices_Big::max;
use crate::Set::Set;
use crate::Set::bot_set;

pub fn sup_nat (x: Set<BigInt>) -> BigInt {
    if <Set<BigInt> as Equal>::equal(x.clone(), bot_set::<BigInt>()) {
        BigInt::ZERO
    } else {
        max(x.clone())
    }
}
