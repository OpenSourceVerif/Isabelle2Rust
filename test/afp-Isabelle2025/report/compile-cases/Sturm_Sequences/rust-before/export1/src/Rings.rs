use crate::Arith::AbGroupAdd;
use crate::Arith::AbSemigroupAdd;
use crate::Arith::AbSemigroupMult;
use crate::Arith::CancelCommMonoidAdd;
use crate::Arith::CommMonoidAdd;
use crate::Arith::CommMonoidMult;
use crate::Arith::NegNumeral;
use crate::Arith::One;
use crate::Arith::SemigroupMult;
use crate::Arith::SemiringNumeral;
use crate::Arith::Times;
use crate::Arith::Zero;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::Semiring_Normalization::CommSemiring1CancelCrossproduct;

pub trait Dvd : Times {
    
}

impl<T : Times> Dvd for T {}

pub trait MultZero : Times + Zero {
    
}

impl<T : Times + Zero> MultZero for T {}

pub trait Semiring : AbSemigroupAdd + SemigroupMult {
    
}

impl<T : AbSemigroupAdd + SemigroupMult> Semiring for T {}

pub trait Semiring0 : CommMonoidAdd + MultZero + Semiring {
    
}

impl<T : CommMonoidAdd + MultZero + Semiring> Semiring0 for T {}

pub trait SemiringNoZeroDivisors : Semiring0 {
    
}

impl<T : Semiring0> SemiringNoZeroDivisors for T {}

pub trait ZeroNeqOne : One + Zero {
    
}

impl<T : One + Zero> ZeroNeqOne for T {}

pub trait Semiring1 : SemiringNumeral + Semiring0 + ZeroNeqOne {
    
}

impl<T : SemiringNumeral + Semiring0 + ZeroNeqOne> Semiring1 for T {}

pub trait Semiring1NoZeroDivisors : Semiring1 + SemiringNoZeroDivisors {
    
}

impl<T : Semiring1 + SemiringNoZeroDivisors> Semiring1NoZeroDivisors for T {}

pub trait Semiring0Cancel : CancelCommMonoidAdd + Semiring0 {
    
}

impl<T : CancelCommMonoidAdd + Semiring0> Semiring0Cancel for T {}

pub trait CommSemiring : AbSemigroupMult + Semiring {
    
}

impl<T : AbSemigroupMult + Semiring> CommSemiring for T {}

pub trait CommSemiring0 : CommSemiring + Semiring0 {
    
}

impl<T : CommSemiring + Semiring0> CommSemiring0 for T {}

pub trait CommSemiring0Cancel : CommSemiring0 + Semiring0Cancel {
    
}

impl<T : CommSemiring0 + Semiring0Cancel> CommSemiring0Cancel for T {}

pub trait Semiring1Cancel : Semiring0Cancel + Semiring1 {
    
}

impl<T : Semiring0Cancel + Semiring1> Semiring1Cancel for T {}

pub trait CommSemiring1 : CommMonoidMult + CommSemiring0 + Semiring1 {
    
}

impl<T : CommMonoidMult + CommSemiring0 + Semiring1> CommSemiring1 for T {}

pub trait CommSemiring1Cancel : CommSemiring0Cancel + CommSemiring1 +
                               Semiring1Cancel {
    
}

impl<T : CommSemiring0Cancel + CommSemiring1 +
        Semiring1Cancel> CommSemiring1Cancel for T {}

pub trait Semidom : CommSemiring1Cancel + Semiring1NoZeroDivisors {
    
}

impl<T : CommSemiring1Cancel + Semiring1NoZeroDivisors> Semidom for T {}

pub trait SemiringNoZeroDivisorsCancel : SemiringNoZeroDivisors {
    
}

impl<T : SemiringNoZeroDivisors> SemiringNoZeroDivisorsCancel for T {}

pub trait Ring : AbGroupAdd + Semiring0Cancel {
    
}

impl<T : AbGroupAdd + Semiring0Cancel> Ring for T {}

pub trait RingNoZeroDivisors : Ring + SemiringNoZeroDivisorsCancel {
    
}

impl<T : Ring + SemiringNoZeroDivisorsCancel> RingNoZeroDivisors for T {}

pub trait Ring1 : NegNumeral + Ring + Semiring1Cancel {
    
}

impl<T : NegNumeral + Ring + Semiring1Cancel> Ring1 for T {}

pub trait Ring1NoZeroDivisors : Ring1 + RingNoZeroDivisors +
                               Semiring1NoZeroDivisors {
    
}

impl<T : Ring1 + RingNoZeroDivisors +
        Semiring1NoZeroDivisors> Ring1NoZeroDivisors for T {}

pub trait CommRing : CommSemiring0Cancel + Ring {
    
}

impl<T : CommSemiring0Cancel + Ring> CommRing for T {}

pub trait CommRing1 : CommRing + CommSemiring1Cancel + Ring1 {
    
}

impl<T : CommRing + CommSemiring1Cancel + Ring1> CommRing1 for T {}

pub trait Idom : CommRing1 + Ring1NoZeroDivisors + Semidom +
                CommSemiring1CancelCrossproduct {
    
}

impl<T : CommRing1 + Ring1NoZeroDivisors + Semidom +
        CommSemiring1CancelCrossproduct> Idom for T {}

pub trait Divide {
    fn divide (x0: Self, x1: Self) -> Self where Self: Sized;
}

pub trait Modulo : Divide + Dvd {
    fn modulo (x0: Self, x1: Self) -> Self where Self: Sized;
}

pub trait DivideTrivial : One + Zero + Divide {
    
}

impl<T : One + Zero + Divide> DivideTrivial for T {}

pub trait SemidomDivide : DivideTrivial + Semidom +
                         SemiringNoZeroDivisorsCancel {
    
}

impl<T : DivideTrivial + Semidom +
        SemiringNoZeroDivisorsCancel> SemidomDivide for T {}

pub trait IdomDivide : Idom + SemidomDivide {
    
}

impl<T : Idom + SemidomDivide> IdomDivide for T {}

pub trait AlgebraicSemidom : SemidomDivide {
    
}

impl<T : SemidomDivide> AlgebraicSemidom for T {}

pub trait SemiringModulo : CommSemiring1Cancel + Modulo {
    
}

impl<T : CommSemiring1Cancel + Modulo> SemiringModulo for T {}

pub trait SemiringModuloTrivial : DivideTrivial + SemiringModulo {
    
}

impl<T : DivideTrivial + SemiringModulo> SemiringModuloTrivial for T {}

pub trait SemidomModulo : AlgebraicSemidom + SemiringModuloTrivial {
    
}

impl<T : AlgebraicSemidom + SemiringModuloTrivial> SemidomModulo for T {}

pub trait UnitFactor {
    fn unit_factor (x0: Self) -> Self where Self: Sized;
}

pub trait SemidomDivideUnitFactor : SemidomDivide + UnitFactor {
    
}

impl<T : SemidomDivide + UnitFactor> SemidomDivideUnitFactor for T {}

pub trait NormalizationSemidom : AlgebraicSemidom + SemidomDivideUnitFactor {
    fn normalize (x0: Self) -> Self where Self: Sized;
}

pub trait NormalizationSemidomMultiplicative : NormalizationSemidom {
    
}

impl<T : NormalizationSemidom> NormalizationSemidomMultiplicative for T {}

pub fn dvd <A> (a: A, b: A) -> bool
where
    A : Clone + Equal + SemidomModulo + 'static
{
    eq(<A as Modulo>::modulo(b.clone(), a.clone()), <A as Zero>::zero())
}
