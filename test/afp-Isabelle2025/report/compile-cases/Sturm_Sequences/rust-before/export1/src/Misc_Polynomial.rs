use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::Sgn;
use crate::Arith::Uminus;
use crate::Polynomial::Poly;
use crate::Polynomial::coeff;
use crate::Polynomial::degree;
use crate::Real_Vector_Spaces::RealNormedVector;
use crate::Rings::dvd;

pub fn poly_inf <A> (p: Poly<A>) -> A
where
    A : Clone + RealNormedVector + 'static
{
    <A as Sgn>::sgn((*coeff(p.clone()))(degree(p.clone())))
}

pub fn poly_neg_inf <A> (p: Poly<A>) -> A
where
    A : Clone + RealNormedVector + 'static
{
    if dvd((match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), degree(p.clone())) {
        <A as Sgn>::sgn((*coeff(p.clone()))(degree(p.clone())))
    } else {
        <A as Uminus>::uminus(<A as Sgn>::sgn((*coeff(p.clone()))(degree(p.clone()))))
    }
}
