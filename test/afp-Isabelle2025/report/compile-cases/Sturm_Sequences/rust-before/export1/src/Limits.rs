use crate::Arith::AbGroupAdd;
use crate::Arith::CommMonoidAdd;
use crate::Arith::GroupAdd;
use crate::Arith::MonoidAdd;
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
