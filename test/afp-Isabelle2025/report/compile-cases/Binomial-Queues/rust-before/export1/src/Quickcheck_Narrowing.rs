use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Code_Evaluation::Term;
use crate::List::List;
use crate::Pure::Itself;
use crate::Typerep::Typerep;

#[derive(Clone)]
pub enum NarrowingType {
    NarrowingSumOfProducts (Box<List<List<NarrowingType>>>)
}

#[derive(Clone)]
pub enum NarrowingTerm {
    NarrowingVariable (List<BigInt>, NarrowingType),
    NarrowingConstructor (BigInt, Box<List<NarrowingTerm>>)
}

pub trait PartialTermOf : Typerep {
    fn partial_term_of (x0: Itself<Self>,
                        x1: NarrowingTerm) -> Term where Self: Sized;
}
