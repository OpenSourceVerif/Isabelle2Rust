use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Natural;
use crate::Arith::nat_of_natural;
use crate::Arith::one_natural;
use crate::Arith::plus_natural;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::Product_Type::Unit;
use crate::Product_Type::scomp;
use crate::Random::rangea;
use crate::Typerep::Typerep;

use std::rc::Rc;

pub trait Random : Typerep {
    fn random (x0: Natural,
               x1: (Natural, Natural)) -> ((Self, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) where Self: Sized;
}

impl Random for BigInt {
    fn random
        (i: Natural,
          eta_arg_0: (Natural, Natural)) -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
        (*scomp(
            (({
                let i_cap = i.clone();
                Rc::new(move |a: (Natural, Natural)| -> (Natural, (Natural, Natural)) {
                    (*rangea(plus_natural(i_cap.clone(), one_natural())))(a.clone())
                })
            }) as Rc<dyn Fn((Natural, Natural)) -> (Natural, (Natural, Natural))>),
            ((Rc::new(move |k: Natural, eta_arg: (Natural, Natural)| -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                (
                    {
                        let n = nat_of_natural(k.clone());
                        (
                            n.clone(),
                            (({
                                let n_cap = n.clone();
                                Rc::new(move |_: Unit| -> Term {
                                    <BigInt as TermOf>::term_of(n_cap.clone())
                                })
                            }) as Rc<dyn Fn(Unit) -> Term>)
                        )
                    },
                    eta_arg.clone()
                )
            })) as Rc<dyn Fn(Natural,
                              (Natural, Natural)) -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
        ))(eta_arg_0.clone())
    }
}
