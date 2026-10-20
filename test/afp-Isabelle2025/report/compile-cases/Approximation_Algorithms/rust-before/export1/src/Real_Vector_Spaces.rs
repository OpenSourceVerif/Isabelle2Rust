use crate::Arith::AbGroupAdd;
use crate::Arith::Minus;
use crate::Arith::RingChar0;
use crate::Arith::Sgn;
use crate::Fields::DivisionRing;
use crate::Fields::FieldChar0;
use crate::Limits::CommRealNormedAlgebra1;
use crate::Limits::TopologicalAbGroupAdd;
use crate::Limits::TopologicalSemigroupMult;
use crate::Real::Real;
use crate::Rings::Ring;
use crate::Topological_Spaces::FirstCountableTopology;
use crate::Topological_Spaces::PerfectSpace;
use crate::Topological_Spaces::T2Space;
use crate::Topological_Spaces::UniformSpace;
use crate::Topological_Spaces::Uniformity;

pub trait Norm {
    fn norm (x0: Self) -> Real where Self: Sized;
}

pub trait Dist {
    fn dist (x0: Self, x1: Self) -> Real where Self: Sized;
}

pub trait DistNorm : Minus + Dist + Norm {
    
}

impl<T : Minus + Dist + Norm> DistNorm for T {}

pub trait ScaleR {
    fn scaler (x0: Real, x1: Self) -> Self where Self: Sized;
}

pub trait RealVector : AbGroupAdd + ScaleR {
    
}

impl<T : AbGroupAdd + ScaleR> RealVector for T {}

pub trait RealAlgebra : RealVector + Ring {
    
}

impl<T : RealVector + Ring> RealAlgebra for T {}

pub trait RealAlgebra1 : RingChar0 + RealAlgebra {
    
}

impl<T : RingChar0 + RealAlgebra> RealAlgebra1 for T {}

pub trait RealDivAlgebra : DivisionRing + RealAlgebra1 {
    
}

impl<T : DivisionRing + RealAlgebra1> RealDivAlgebra for T {}

pub trait RealField : FieldChar0 + RealDivAlgebra {
    
}

impl<T : FieldChar0 + RealDivAlgebra> RealField for T {}

pub trait UniformityDist : Dist + Uniformity {
    
}

impl<T : Dist + Uniformity> UniformityDist for T {}

pub trait MetricSpace : UniformityDist + FirstCountableTopology + T2Space +
                       UniformSpace {
    
}

impl<T : UniformityDist + FirstCountableTopology + T2Space +
        UniformSpace> MetricSpace for T {}

pub trait SgnDivNorm : Sgn + Norm + ScaleR {
    
}

impl<T : Sgn + Norm + ScaleR> SgnDivNorm for T {}

pub trait RealNormedVector : TopologicalAbGroupAdd + DistNorm + MetricSpace +
                            RealVector + SgnDivNorm {
    
}

impl<T : TopologicalAbGroupAdd + DistNorm + MetricSpace + RealVector +
        SgnDivNorm> RealNormedVector for T {}

pub trait RealNormedAlgebra : TopologicalSemigroupMult + RealAlgebra +
                             RealNormedVector {
    
}

impl<T : TopologicalSemigroupMult + RealAlgebra +
        RealNormedVector> RealNormedAlgebra for T {}

pub trait RealNormedAlgebra1 : RealAlgebra1 + RealNormedAlgebra + PerfectSpace {
    
}

impl<T : RealAlgebra1 + RealNormedAlgebra +
        PerfectSpace> RealNormedAlgebra1 for T {}

pub trait RealNormedDivAlgebra : RealDivAlgebra + RealNormedAlgebra1 {
    
}

impl<T : RealDivAlgebra + RealNormedAlgebra1> RealNormedDivAlgebra for T {}

pub trait RealNormedField : CommRealNormedAlgebra1 + RealField +
                           RealNormedDivAlgebra {
    
}

impl<T : CommRealNormedAlgebra1 + RealField +
        RealNormedDivAlgebra> RealNormedField for T {}
