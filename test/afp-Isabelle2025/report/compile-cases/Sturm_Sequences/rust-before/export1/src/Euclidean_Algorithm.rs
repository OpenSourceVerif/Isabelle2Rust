use crate::Arith::One;
use crate::Arith::Times;
use crate::Arith::Zero;
use crate::Euclidean_Rings::EuclideanSemiring;
use crate::Factorial_Ring::FactorialSemiring;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::fold;
use crate::Rings::Divide;
use crate::Rings::Modulo;
use crate::Rings::NormalizationSemidom;
use crate::Set::Set;

use std::rc::Rc;

pub trait NormalizationEuclideanSemiring : EuclideanSemiring +
  FactorialSemiring {
    
}

impl<T : EuclideanSemiring +
        FactorialSemiring> NormalizationEuclideanSemiring for T {}

pub fn gcda <A> (a: A, b: A) -> A
where
    A : Clone + NormalizationEuclideanSemiring + Equal + 'static
{
    if eq(b.clone(), <A as Zero>::zero()) {
        <A as NormalizationSemidom>::normalize(a.clone())
    } else {
        gcda(b.clone(), <A as Modulo>::modulo(a.clone(), b.clone()))
    }
}

pub fn gcd <A> (x0: Set<A>) -> A
where
    A : Clone + NormalizationEuclideanSemiring + Equal + 'static
{
    match x0 {
        Set::Set (xs) =>
            fold(((Rc::new(move |a: A, b: A| -> A {
                gcda(a.clone(), b.clone())
            })) as Rc<dyn Fn(A, A) -> A>), xs.clone(), <A as Zero>::zero()),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn lcma <A> (a: A, b: A) -> A
where
    A : Clone + NormalizationEuclideanSemiring + Equal + 'static
{
    <A as NormalizationSemidom>::normalize(<A as Divide>::divide(<A as Times>::times(a.clone(), b.clone()), gcda(a.clone(), b.clone())))
}

pub fn lcm <A> (x0: Set<A>) -> A
where
    A : Clone + NormalizationEuclideanSemiring + Equal + 'static
{
    match x0 {
        Set::Set (xs) =>
            fold(((Rc::new(move |a: A, b: A| -> A {
                lcma(a.clone(), b.clone())
            })) as Rc<dyn Fn(A, A) -> A>), xs.clone(), <A as One>::one()),
        _ =>
            panic!("non-exhaustive match")
    }
}
