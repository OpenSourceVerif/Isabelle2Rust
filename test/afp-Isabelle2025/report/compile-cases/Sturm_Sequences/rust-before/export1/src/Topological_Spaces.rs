use crate::Filter::Filter;
use crate::Set::Set;

pub trait Open {
    fn opena (x0: Set<Self>) -> bool where Self: Sized;
}

pub trait TopologicalSpace : Open {
    
}

impl<T : Open> TopologicalSpace for T {}

pub trait T0Space : TopologicalSpace {
    
}

impl<T : TopologicalSpace> T0Space for T {}

pub trait T1Space : T0Space {
    
}

impl<T : T0Space> T1Space for T {}

pub trait T2Space : T1Space {
    
}

impl<T : T1Space> T2Space for T {}

pub trait Uniformity {
    fn uniformity () -> Filter<(Self, Self)> where Self: Sized;
}

pub trait OpenUniformity : TopologicalSpace + Uniformity {
    
}

impl<T : TopologicalSpace + Uniformity> OpenUniformity for T {}

pub trait UniformSpace : OpenUniformity {
    
}

impl<T : OpenUniformity> UniformSpace for T {}

pub trait FirstCountableTopology : TopologicalSpace {
    
}

impl<T : TopologicalSpace> FirstCountableTopology for T {}
