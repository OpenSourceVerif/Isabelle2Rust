use crate::Rings::Divide;
use crate::Rings::DivideTrivial;
use crate::Rings::IdomDivide;
use crate::Rings::Ring1NoZeroDivisors;

pub trait Inverse : Divide {
    fn inverse (x0: Self) -> Self where Self: Sized;
}

pub trait DivisionRing : Inverse + DivideTrivial + Ring1NoZeroDivisors {
    
}

impl<T : Inverse + DivideTrivial + Ring1NoZeroDivisors> DivisionRing for T {}

pub trait Field : DivisionRing + IdomDivide {
    
}

impl<T : DivisionRing + IdomDivide> Field for T {}
