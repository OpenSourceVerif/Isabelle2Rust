use crate::Arith::AbGroupAdd;
use crate::Arith::AbSemigroupAdd;
use crate::Arith::AbSemigroupMult;
use crate::Arith::CancelAbSemigroupAdd;
use crate::Arith::CancelCommMonoidAdd;
use crate::Arith::CancelSemigroupAdd;
use crate::Arith::CommMonoidAdd;
use crate::Arith::CommMonoidMult;
use crate::Arith::GroupAdd;
use crate::Arith::Minus;
use crate::Arith::MonoidAdd;
use crate::Arith::MonoidMult;
use crate::Arith::NegNumeral;
use crate::Arith::Numeral;
use crate::Arith::One;
use crate::Arith::Plus;
use crate::Arith::Power;
use crate::Arith::SemigroupAdd;
use crate::Arith::SemigroupMult;
use crate::Arith::SemiringNumeral;
use crate::Arith::Sgn;
use crate::Arith::Times;
use crate::Arith::Uminus;
use crate::Arith::Zero;
use crate::Fields::DivisionRing;
use crate::Fields::Field;
use crate::Fields::Inverse;
use crate::HOL::Equal;
use crate::Rat::Rat;
use crate::Rat::less_rat;
use crate::Rings::CommRing;
use crate::Rings::CommRing1;
use crate::Rings::CommSemiring;
use crate::Rings::CommSemiring0;
use crate::Rings::CommSemiring0Cancel;
use crate::Rings::CommSemiring1;
use crate::Rings::CommSemiring1Cancel;
use crate::Rings::Divide;
use crate::Rings::DivideTrivial;
use crate::Rings::Dvd;
use crate::Rings::Idom;
use crate::Rings::IdomDivide;
use crate::Rings::MultZero;
use crate::Rings::Ring;
use crate::Rings::Ring1;
use crate::Rings::Ring1NoZeroDivisors;
use crate::Rings::RingNoZeroDivisors;
use crate::Rings::Semidom;
use crate::Rings::SemidomDivide;
use crate::Rings::Semiring;
use crate::Rings::Semiring0;
use crate::Rings::Semiring0Cancel;
use crate::Rings::Semiring1;
use crate::Rings::Semiring1Cancel;
use crate::Rings::Semiring1NoZeroDivisors;
use crate::Rings::SemiringNoZeroDivisors;
use crate::Rings::SemiringNoZeroDivisorsCancel;
use crate::Rings::ZeroNeqOne;
use crate::Semiring_Normalization::CommSemiring1CancelCrossproduct;

#[derive(Clone)]
pub enum Real {
    Ratreal (Rat)
}

impl Equal for Real {
    fn equal (x0: Real, x1: Real) -> bool {
        let (Real::Ratreal (x), Real::Ratreal (y)) = (x0, x1);
        <Rat as Equal>::equal(x.clone(), y.clone())
    }
}

impl Times for Real {
    fn times (x0: Real, x1: Real) -> Real {
        let (Real::Ratreal (x), Real::Ratreal (y)) = (x0, x1);
        Real::Ratreal (<Rat as Times>::times(x.clone(), y.clone()))
    }
}

impl One for Real {
    fn one () -> Real {
        Real::Ratreal (<Rat as One>::one())
    }
}

impl Uminus for Real {
    fn uminus (x0: Real) -> Real {
        let Real::Ratreal (x) = x0;
        Real::Ratreal (<Rat as Uminus>::uminus(x.clone()))
    }
}

impl Zero for Real {
    fn zero () -> Real {
        Real::Ratreal (<Rat as Zero>::zero())
    }
}

pub fn less_real (x0: Real, x1: Real) -> bool {
    let (Real::Ratreal (x), Real::Ratreal (y)) = (x0, x1);
    less_rat(x.clone(), y.clone())
}

impl Sgn for Real {
    fn sgn (a: Real) -> Real {
        if <Real as Equal>::equal(a.clone(), <Real as Zero>::zero()) {
            <Real as Zero>::zero()
        } else {
            if less_real(<Real as Zero>::zero(), a.clone()) {
                <Real as One>::one()
            } else {
                <Real as Uminus>::uminus(<Real as One>::one())
            }
        }
    }
}

impl Minus for Real {
    fn minus (x0: Real, x1: Real) -> Real {
        let (Real::Ratreal (x), Real::Ratreal (y)) = (x0, x1);
        Real::Ratreal (<Rat as Minus>::minus(x.clone(), y.clone()))
    }
}

impl Plus for Real {
    fn plus (x0: Real, x1: Real) -> Real {
        let (Real::Ratreal (x), Real::Ratreal (y)) = (x0, x1);
        Real::Ratreal (<Rat as Plus>::plus(x.clone(), y.clone()))
    }
}

impl Inverse for Real {
    fn inverse (x0: Real) -> Real {
        let Real::Ratreal (x) = x0;
        Real::Ratreal (<Rat as Inverse>::inverse(x.clone()))
    }
}

impl Divide for Real {
    fn divide (x0: Real, x1: Real) -> Real {
        let (Real::Ratreal (x), Real::Ratreal (y)) = (x0, x1);
        Real::Ratreal (<Rat as Divide>::divide(x.clone(), y.clone()))
    }
}

pub fn abs_real (a: Real) -> Real {
    if less_real(a.clone(), <Real as Zero>::zero()) {
        <Real as Uminus>::uminus(a.clone())
    } else {
        a.clone()
    }
}
