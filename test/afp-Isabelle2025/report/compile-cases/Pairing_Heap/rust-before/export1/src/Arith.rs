use num_bigint::*;
use num_traits::sign::Signed as _;

pub trait Plus {
    fn plus (x0: Self, x1: Self) -> Self where Self: Sized;
}

pub trait SemigroupAdd : Plus {
    
}

impl<T : Plus> SemigroupAdd for T {}

pub trait Zero {
    fn zero () -> Self where Self: Sized;
}

pub trait MonoidAdd : SemigroupAdd + Zero {
    
}

impl<T : SemigroupAdd + Zero> MonoidAdd for T {}

pub trait AbSemigroupAdd : SemigroupAdd {
    
}

impl<T : SemigroupAdd> AbSemigroupAdd for T {}

pub trait CommMonoidAdd : AbSemigroupAdd + MonoidAdd {
    
}

impl<T : AbSemigroupAdd + MonoidAdd> CommMonoidAdd for T {}

#[derive(Clone)]
pub enum Num {
    One,
    Bit0 (Box<Num>),
    Bit1 (Box<Num>)
}

pub fn one_nat () -> BigInt {
    BigInt::from_bytes_be(Sign::Plus, &[1])
}

pub fn suc (n: BigInt) -> BigInt {
    n.clone() + one_nat()
}
