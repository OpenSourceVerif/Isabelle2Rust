use crate::GCD::RingGcd;
use crate::GCD::SemiringGcd;
use crate::Rings::IdomDivide;
use crate::Rings::NormalizationSemidom;

pub trait FactorialSemiring : NormalizationSemidom {
    
}

impl<T : NormalizationSemidom> FactorialSemiring for T {}

pub trait FactorialSemiringGcd : FactorialSemiring + SemiringGcd {
    
}

impl<T : FactorialSemiring + SemiringGcd> FactorialSemiringGcd for T {}

pub trait FactorialRingGcd : FactorialSemiringGcd + RingGcd + IdomDivide {
    
}

impl<T : FactorialSemiringGcd + RingGcd + IdomDivide> FactorialRingGcd for T {}
