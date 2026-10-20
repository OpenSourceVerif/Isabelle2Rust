use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::One;
use crate::Arith::Zero;
use crate::Rings::CommRing1;
use crate::Rings::Dvd;
use crate::Rings::Modulo;
use crate::Rings::NormalizationSemidom;
use crate::Rings::NormalizationSemidomMultiplicative;
use crate::Set::Set;

pub trait Gcda : One + Zero + Dvd {
    fn gcda (x0: Self, x1: Self) -> Self where Self: Sized;
    fn lcma (x0: Self, x1: Self) -> Self where Self: Sized;
}

pub trait Gcd : Gcda {
    fn gcd (x0: Set<Self>) -> Self where Self: Sized;
    fn lcm (x0: Set<Self>) -> Self where Self: Sized;
}

pub trait SemiringGcda : Gcda + NormalizationSemidom {
    
}

impl<T : Gcda + NormalizationSemidom> SemiringGcda for T {}

pub trait RingGcd : SemiringGcda + CommRing1 {
    
}

impl<T : SemiringGcda + CommRing1> RingGcd for T {}

pub trait SemiringGcd : Gcd + SemiringGcda {
    
}

impl<T : Gcd + SemiringGcda> SemiringGcd for T {}

pub trait SemiringGcdMultNormalize : SemiringGcda +
                                    NormalizationSemidomMultiplicative {
    
}

impl<T : SemiringGcda +
        NormalizationSemidomMultiplicative> SemiringGcdMultNormalize for T {}

impl Gcda for BigInt {
    fn gcda (k: BigInt, l: BigInt) -> BigInt {
        (if l.clone() == BigInt::ZERO {
              k.clone()
          } else {
              <BigInt as Gcda>::gcda(l.clone(), <BigInt as Modulo>::modulo((k.clone().abs()), (l.clone().abs())))
          }.abs())
    }
    fn lcma (x0: Self,
             x1: Self) -> Self { panic!("unimplemented instance method: lcma") }
}
