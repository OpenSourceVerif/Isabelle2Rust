use crate::Arith::AbGroupAdd;
use crate::Arith::CommMonoidAdd;
use crate::Arith::CommMonoidMult;
use crate::Arith::GroupAdd;
use crate::Arith::MonoidAdd;
use crate::Arith::SemigroupMult;
use crate::Real_Vector_Spaces::RealNormedAlgebra1;
use crate::Topological_Spaces::TopologicalSpace;

pub trait TopologicalMonoidAdd : MonoidAdd + TopologicalSpace {
    
}

impl<T : MonoidAdd + TopologicalSpace> TopologicalMonoidAdd for T {}

pub trait TopologicalGroupAdd : GroupAdd + TopologicalMonoidAdd {
    
}

impl<T : GroupAdd + TopologicalMonoidAdd> TopologicalGroupAdd for T {}

pub trait TopologicalCommMonoidAdd : CommMonoidAdd + TopologicalMonoidAdd {
    
}

impl<T : CommMonoidAdd + TopologicalMonoidAdd> TopologicalCommMonoidAdd for T {}

pub trait TopologicalAbGroupAdd : AbGroupAdd + TopologicalCommMonoidAdd +
                                 TopologicalGroupAdd {
    
}

impl<T : AbGroupAdd + TopologicalCommMonoidAdd +
        TopologicalGroupAdd> TopologicalAbGroupAdd for T {}

pub trait CommRealNormedAlgebra1 : CommMonoidMult + RealNormedAlgebra1 {
    
}

impl<T : CommMonoidMult + RealNormedAlgebra1> CommRealNormedAlgebra1 for T {}

pub trait TopologicalSemigroupMult : SemigroupMult + TopologicalSpace {
    
}

impl<T : SemigroupMult + TopologicalSpace> TopologicalSemigroupMult for T {}
