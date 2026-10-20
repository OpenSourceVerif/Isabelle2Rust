use crate::Arith::AbGroupAdd;
use crate::Arith::CommMonoidAdd;
use crate::Arith::GroupAdd;
use crate::Arith::Minus;
use crate::Arith::MonoidAdd;
use crate::Arith::Plus;
use crate::Arith::Sgn;
use crate::Arith::Times;
use crate::Arith::Uminus;
use crate::Arith::Zero;
use crate::Filter::Filter;
use crate::Limits::TopologicalAbGroupAdd;
use crate::Limits::TopologicalCommMonoidAdd;
use crate::Limits::TopologicalGroupAdd;
use crate::Limits::TopologicalMonoidAdd;
use crate::Product_Type::Unit;
use crate::Real::Real;
use crate::Real::abs_real;
use crate::Set::Set;
use crate::String::Literal;
use crate::Topological_Spaces::FirstCountableTopology;
use crate::Topological_Spaces::Open;
use crate::Topological_Spaces::OpenUniformity;
use crate::Topological_Spaces::T0Space;
use crate::Topological_Spaces::T1Space;
use crate::Topological_Spaces::T2Space;
use crate::Topological_Spaces::TopologicalSpace;
use crate::Topological_Spaces::UniformSpace;
use crate::Topological_Spaces::Uniformity;

use std::rc::Rc;

impl Dist for Real {
    fn dist (x: Real, y: Real) -> Real {
        abs_real(<Real as Minus>::minus(x.clone(), y.clone()))
    }
}

pub trait Dist {
    fn dist (x0: Self, x1: Self) -> Real where Self: Sized;
}

impl Norm for Real {
    fn norm (r: Real) -> Real {
        abs_real(r.clone())
    }
}

pub trait Norm {
    fn norm (x0: Self) -> Real where Self: Sized;
}

impl Open for Real {
    fn opena (x0: Set<Self>) -> bool { panic!("unimplemented instance method: opena") }
}

impl ScaleR for Real {
    fn scaler (a: Real, x: Real) -> Real {
        <Real as Times>::times(a.clone(), x.clone())
    }
}

pub trait ScaleR {
    fn scaler (x0: Real, x1: Self) -> Self where Self: Sized;
}

pub trait DistNorm : Minus + Dist + Norm {
    
}

impl<T : Minus + Dist + Norm> DistNorm for T {}

impl Uniformity for Real {
    fn uniformity () -> Filter<(Real, Real)> {
        Filter::AbstractFilter (
            Box::new(((Rc::new(move |_: Unit| -> Filter<(Real, Real)> {
                  panic!( Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, false, true, false, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, false, false, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, false, false, true, false, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))) )
                    ((Rc::new(move |_: Unit| -> Filter<(Real, Real)> {
                        <Real as Uniformity>::uniformity()
                    })) as Rc<dyn Fn(Unit) -> Filter<(Real, Real)>>)
              })) as Rc<dyn Fn(Unit) -> Filter<(Real, Real)>>))
        )
    }
}

pub trait RealVector : AbGroupAdd + ScaleR {
    
}

impl<T : AbGroupAdd + ScaleR> RealVector for T {}

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
