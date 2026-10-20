use crate::Rat::Rat;
use crate::Rat::divide_rat;
use crate::Rat::uminus_rat;

#[derive(Clone)]
pub enum Real {
    Ratreal (Rat)
}

pub fn divide_real (x0: Real, x1: Real) -> Real {
    let (Real::Ratreal (x), Real::Ratreal (y)) = (x0, x1);
    Real::Ratreal (divide_rat(x.clone(), y.clone()))
}

pub fn uminus_real (x0: Real) -> Real {
    let Real::Ratreal (x) = x0;
    Real::Ratreal (uminus_rat(x.clone()))
}
