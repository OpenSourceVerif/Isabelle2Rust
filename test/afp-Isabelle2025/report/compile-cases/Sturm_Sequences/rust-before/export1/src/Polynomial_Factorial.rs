use crate::Factorial_Ring::FactorialRingGcd;
use crate::GCD::Gcda;
use crate::GCD::SemiringGcdMultNormalize;
use crate::HOL::Equal;
use crate::Polynomial::Poly;
use crate::Polynomial::content;
use crate::Polynomial::is_zero;
use crate::Polynomial::primitive_part;
use crate::Polynomial::pseudo_mod;
use crate::Polynomial::smult;
use crate::Rings::NormalizationSemidom;

pub fn gcd_poly_code_aux <A> (p: Poly<A>, q: Poly<A>) -> Poly<A>
where
    A : Clone + crate::Arith::Zero + crate::Rings::IdomDivide +
               crate::Rings::SemidomDivideUnitFactor + FactorialRingGcd +
               Equal + 'static
{
    if is_zero(q.clone()) {
        <Poly<A> as NormalizationSemidom>::normalize(p.clone())
    } else {
        gcd_poly_code_aux(q.clone(), primitive_part(pseudo_mod(p.clone(), q.clone())))
    }
}

pub fn gcd_poly_code <A> (p: Poly<A>, q: Poly<A>) -> Poly<A>
where
    A : Clone + crate::Arith::Zero + crate::Rings::IdomDivide +
               crate::Rings::SemidomDivideUnitFactor + FactorialRingGcd +
               Equal + 'static
{
    if is_zero(p.clone()) {
        <Poly<A> as NormalizationSemidom>::normalize(q.clone())
    } else {
        if is_zero(q.clone()) {
            <Poly<A> as NormalizationSemidom>::normalize(p.clone())
        } else {
            smult(<A as Gcda>::gcda(content(p.clone()), content(q.clone())), gcd_poly_code_aux(primitive_part(p.clone()), primitive_part(q.clone())))
        }
    }
}

impl <A : Clone + crate::Arith::Zero + FactorialRingGcd +
                 SemiringGcdMultNormalize + Equal + 'static>
    Gcda for Poly<A> {
    fn gcda (p: Poly<A>, q: Poly<A>) -> Poly<A> {
        gcd_poly_code(p.clone(), q.clone())
    }
    fn lcma (x0: Self,
             x1: Self) -> Self { panic!("unimplemented instance method: lcma") }
}
