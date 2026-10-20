use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Minus;
use crate::Arith::One;
use crate::Arith::Plus;
use crate::Arith::Times;
use crate::Arith::Zero;
use crate::Rings::AlgebraicSemidom;
use crate::Rings::CommSemiring1Cancel;
use crate::Rings::Divide;
use crate::Rings::DivideTrivial;
use crate::Rings::Dvd;
use crate::Rings::Modulo;
use crate::Rings::Semidom;
use crate::Rings::SemidomDivide;
use crate::Rings::SemidomModulo;
use crate::Rings::SemiringModulo;
use crate::Rings::SemiringModuloTrivial;
use crate::Rings::SemiringNoZeroDivisors;
use crate::Rings::SemiringNoZeroDivisorsCancel;

pub trait EuclideanSemiring : SemidomModulo {
    fn euclidean_size (x0: Self) -> BigInt where Self: Sized;
}
