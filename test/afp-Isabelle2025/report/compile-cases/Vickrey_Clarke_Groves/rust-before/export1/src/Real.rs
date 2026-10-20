use crate::Arith::AbSemigroupAdd;
use crate::Arith::CommMonoidAdd;
use crate::Arith::Minus;
use crate::Arith::MonoidAdd;
use crate::Arith::Plus;
use crate::Arith::SemigroupAdd;
use crate::Arith::Zero;
use crate::Orderings::Linorder;
use crate::Orderings::Ord;
use crate::Orderings::Order;
use crate::Orderings::Preorder;
use crate::Rat::Rat;

#[derive(Clone)]
pub enum Real {
    Ratreal (Rat)
}

impl Plus for Real {
    fn plus (x0: Real, x1: Real) -> Real {
        let (Real::Ratreal (x), Real::Ratreal (y)) = (x0, x1);
        Real::Ratreal (<Rat as Plus>::plus(x.clone(), y.clone()))
    }
}

impl Zero for Real {
    fn zero () -> Real {
        Real::Ratreal (<Rat as Zero>::zero())
    }
}

impl Minus for Real {
    fn minus (x0: Real, x1: Real) -> Real {
        let (Real::Ratreal (x), Real::Ratreal (y)) = (x0, x1);
        Real::Ratreal (<Rat as Minus>::minus(x.clone(), y.clone()))
    }
}

impl Ord for Real {
    fn less_eq (x0: Real, x1: Real) -> bool {
        let (Real::Ratreal (x), Real::Ratreal (y)) = (x0, x1);
        <Rat as Ord>::less_eq(x.clone(), y.clone())
    }
    fn less (x0: Real, x1: Real) -> bool {
        let (Real::Ratreal (x), Real::Ratreal (y)) = (x0, x1);
        <Rat as Ord>::less(x.clone(), y.clone())
    }
}
