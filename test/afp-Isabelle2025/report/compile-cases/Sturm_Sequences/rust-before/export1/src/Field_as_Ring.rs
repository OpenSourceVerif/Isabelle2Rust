use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Minus;
use crate::Arith::One;
use crate::Arith::Plus;
use crate::Arith::Times;
use crate::Arith::Uminus;
use crate::Arith::Zero;
use crate::Euclidean_Algorithm::NormalizationEuclideanSemiring;
use crate::Euclidean_Algorithm::gcd;
use crate::Euclidean_Algorithm::gcda;
use crate::Euclidean_Algorithm::lcm;
use crate::Euclidean_Algorithm::lcma;
use crate::Euclidean_Rings::EuclideanSemiring;
use crate::Factorial_Ring::FactorialRingGcd;
use crate::Factorial_Ring::FactorialSemiring;
use crate::Factorial_Ring::FactorialSemiringGcd;
use crate::Fields::Field;
use crate::GCD::Gcd;
use crate::GCD::Gcda;
use crate::GCD::RingGcd;
use crate::GCD::SemiringGcd;
use crate::GCD::SemiringGcdMultNormalize;
use crate::GCD::SemiringGcda;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::Real::Real;
use crate::Rings::AlgebraicSemidom;
use crate::Rings::CommRing1;
use crate::Rings::CommSemiring1Cancel;
use crate::Rings::Divide;
use crate::Rings::DivideTrivial;
use crate::Rings::Dvd;
use crate::Rings::IdomDivide;
use crate::Rings::Modulo;
use crate::Rings::NormalizationSemidom;
use crate::Rings::NormalizationSemidomMultiplicative;
use crate::Rings::SemidomDivide;
use crate::Rings::SemidomDivideUnitFactor;
use crate::Rings::SemidomModulo;
use crate::Rings::SemiringModulo;
use crate::Rings::SemiringModuloTrivial;
use crate::Rings::UnitFactor;
use crate::Set::Set;

pub fn euclidean_size_field <A> (x: A) -> BigInt
where
    A : Clone + Field + Equal + 'static
{
    if eq(x.clone(), <A as Zero>::zero()) {
        BigInt::ZERO
    } else {
        <BigInt as One>::one()
    }
}

impl EuclideanSemiring for Real {
    fn euclidean_size (eta_arg_0: Real) -> BigInt {
        euclidean_size_field(eta_arg_0.clone())
    }
}

pub fn normalize_field <A> (x: A) -> A
where
    A : Clone + Field + Equal + 'static
{
    if eq(x.clone(), <A as Zero>::zero()) {
        <A as Zero>::zero()
    } else {
        <A as One>::one()
    }
}

impl NormalizationSemidom for Real {
    fn normalize (eta_arg_0: Real) -> Real {
        normalize_field(eta_arg_0.clone())
    }
}

pub fn unit_factor_field <A> (x: A) -> A
where
    A : Clone + Field + 'static
{
    x.clone()
}

impl UnitFactor for Real {
    fn unit_factor (eta_arg_0: Real) -> Real {
        unit_factor_field(eta_arg_0.clone())
    }
}

pub fn mod_field <A> (x: A, y: A) -> A
where
    A : Clone + Field + Equal + 'static
{
    if eq(y.clone(), <A as Zero>::zero()) {
        x.clone()
    } else {
        <A as Zero>::zero()
    }
}

impl Modulo for Real {
    fn modulo (eta_arg_0: Real, eta_arg_1: Real) -> Real {
        mod_field(eta_arg_0.clone(), eta_arg_1.clone())
    }
}

impl Gcda for Real {
    fn lcma (eta_arg_0: Real, eta_arg_1: Real) -> Real {
        lcma(eta_arg_0.clone(), eta_arg_1.clone())
    }
    fn gcda (eta_arg_0: Real, eta_arg_1: Real) -> Real {
        gcda(eta_arg_0.clone(), eta_arg_1.clone())
    }
}

impl Gcd for Real {
    fn lcm (eta_arg_0: Set<Real>) -> Real {
        lcm(eta_arg_0.clone())
    }
    fn gcd (eta_arg_0: Set<Real>) -> Real {
        gcd(eta_arg_0.clone())
    }
}
