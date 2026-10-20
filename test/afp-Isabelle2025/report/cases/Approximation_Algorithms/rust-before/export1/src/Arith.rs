use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Euclidean_Rings::divmod_nat;
use crate::Orderings::Ord;
use crate::Rings::Dvd;
use crate::Rings::Ring1;
use crate::Rings::Semiring;
use crate::Rings::Semiring1;

pub trait Plus {
    fn plus (x0: Self, x1: Self) -> Self where Self: Sized;
}

pub trait SemigroupAdd : Plus {
    
}

impl<T : Plus> SemigroupAdd for T {}

pub trait One {
    fn one () -> Self where Self: Sized;
}

pub trait Numeral : One + SemigroupAdd {
    
}

impl<T : One + SemigroupAdd> Numeral for T {}

pub trait Times {
    fn times (x0: Self, x1: Self) -> Self where Self: Sized;
}

pub trait Power : One + Times {
    
}

impl<T : One + Times> Power for T {}

pub trait SemiringChar0 : Semiring1 {
    
}

impl<T : Semiring1> SemiringChar0 for T {}

pub trait RingChar0 : SemiringChar0 + Ring1 {
    
}

impl<T : SemiringChar0 + Ring1> RingChar0 for T {}

pub trait CancelSemigroupAdd : SemigroupAdd {
    
}

impl<T : SemigroupAdd> CancelSemigroupAdd for T {}

pub trait Zero {
    fn zero () -> Self where Self: Sized;
}

pub trait MonoidAdd : SemigroupAdd + Zero {
    
}

impl<T : SemigroupAdd + Zero> MonoidAdd for T {}

pub trait Uminus {
    fn uminus (x0: Self) -> Self where Self: Sized;
}

pub trait Minus {
    fn minus (x0: Self, x1: Self) -> Self where Self: Sized;
}

pub trait GroupAdd : CancelSemigroupAdd + Minus + MonoidAdd + Uminus {
    
}

impl<T : CancelSemigroupAdd + Minus + MonoidAdd + Uminus> GroupAdd for T {}

pub trait NegNumeral : GroupAdd + Numeral {
    
}

impl<T : GroupAdd + Numeral> NegNumeral for T {}

pub trait SemigroupMult : Times {
    
}

impl<T : Times> SemigroupMult for T {}

pub trait MonoidMult : SemigroupMult + Power {
    
}

impl<T : SemigroupMult + Power> MonoidMult for T {}

pub trait AbSemigroupAdd : SemigroupAdd {
    
}

impl<T : SemigroupAdd> AbSemigroupAdd for T {}

pub trait CancelAbSemigroupAdd : AbSemigroupAdd + CancelSemigroupAdd + Minus {
    
}

impl<T : AbSemigroupAdd + CancelSemigroupAdd +
        Minus> CancelAbSemigroupAdd for T {}

pub trait CommMonoidAdd : AbSemigroupAdd + MonoidAdd {
    
}

impl<T : AbSemigroupAdd + MonoidAdd> CommMonoidAdd for T {}

pub trait CancelCommMonoidAdd : CancelAbSemigroupAdd + CommMonoidAdd {
    
}

impl<T : CancelAbSemigroupAdd + CommMonoidAdd> CancelCommMonoidAdd for T {}

pub trait AbGroupAdd : CancelCommMonoidAdd + GroupAdd {
    
}

impl<T : CancelCommMonoidAdd + GroupAdd> AbGroupAdd for T {}

pub trait SemiringNumeral : MonoidMult + Numeral + Semiring {
    
}

impl<T : MonoidMult + Numeral + Semiring> SemiringNumeral for T {}

pub trait AbSemigroupMult : SemigroupMult {
    
}

impl<T : SemigroupMult> AbSemigroupMult for T {}

pub trait CommMonoidMult : AbSemigroupMult + MonoidMult + Dvd {
    
}

impl<T : AbSemigroupMult + MonoidMult + Dvd> CommMonoidMult for T {}

pub trait Sgn {
    fn sgn (x0: Self) -> Self where Self: Sized;
}

#[derive(Clone)]
pub enum Num {
    One,
    Bit0 (Box<Num>),
    Bit1 (Box<Num>)
}

impl One for BigInt {
    fn one () -> BigInt {
        BigInt::from_bytes_be(Sign::Plus, &[1])
    }
}

pub fn suc (n: BigInt) -> BigInt {
    n.clone() + <BigInt as One>::one()
}

pub fn numeral <A> (x0: Num) -> A
where
    A : Clone + Numeral + 'static
{
    match x0 {
        Num::Bit1 (p0) =>
            {
                let n = *p0;
                {
                    let m = numeral::<A>(n.clone());
                    <A as Plus>::plus(<A as Plus>::plus(m.clone(), m.clone()), <A as One>::one())
                }
            },
        Num::Bit0 (p0) =>
            {
                let n = *p0;
                {
                    let m = numeral::<A>(n.clone());
                    <A as Plus>::plus(m.clone(), m.clone())
                }
            },
        Num::One =>
            <A as One>::one(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn of_nat <A> (n: BigInt) -> A
where
    A : Clone + Semiring1 + 'static
{
    if n.clone() == BigInt::ZERO {
        <A as Zero>::zero()
    } else {
        match divmod_nat(n.clone(), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })) {
            (m, q) =>
                {
                    let ma = <A as Times>::times(numeral::<A>(Num::Bit0 (Box::new(Num::One))), of_nat::<A>(m.clone()));
                    if q.clone() == BigInt::ZERO {
                        ma.clone()
                    } else {
                        <A as Plus>::plus(ma.clone(), <A as One>::one())
                    }
                },
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
