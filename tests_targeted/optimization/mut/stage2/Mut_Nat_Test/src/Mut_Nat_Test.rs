use num_bigint::*;
use num_traits::sign::*;
// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn let_mut_nat(n: &BigInt) -> BigInt {
    {
        let mut x = n.clone();
        x = x + crate::Arith::one_nat();
        x = x * (match BigInt::from_bytes_be(Sign::Plus, &vec!(2)).clone() {
            k => {
                if k <= BigInt::ZERO {
                    BigInt::ZERO
                } else {
                    k
                }
            },
        });
        x
    }
}

