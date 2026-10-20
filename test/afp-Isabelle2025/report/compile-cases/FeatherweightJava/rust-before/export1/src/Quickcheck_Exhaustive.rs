use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Natural;
use crate::Arith::Plus;
use crate::Arith::Zero;
use crate::Arith::nat_of_natural;
use crate::Arith::one_natural;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::List::List;
use crate::Option::Option;
use crate::Orderings::Ord;
use crate::Product_Type::Unit;
use crate::Pure::Itself;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;

use std::rc::Rc;

pub fn full_exhaustive_natural
    (f: Rc<dyn Fn((Natural, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>,
      d: Natural, i: Natural) -> Option<(bool, List<Term>)> {
    if <Natural as Ord>::less(d.clone(), i.clone()) {
        Option::None
    } else {
        match (*f)((
              i.clone(),
              (({
                  let i_cap = i.clone();
                  Rc::new(move |_: Unit| -> Term {
                      <Natural as TermOf>::term_of(i_cap.clone())
                  })
              }) as Rc<dyn Fn(Unit) -> Term>)
          )) {
            Option::None =>
                full_exhaustive_natural(f.clone(), d.clone(), <Natural as Plus>::plus(i.clone(), one_natural())),
            Option::Some (a) =>
                Option::Some (a.clone()),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl FullExhaustive for Natural {
    fn full_exhaustive
        (f: Rc<dyn Fn((Natural, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>,
          d: Natural) -> Option<(bool, List<Term>)> {
        full_exhaustive_natural(f.clone(), d.clone(), <Natural as Zero>::zero())
    }
}

impl FullExhaustive for BigInt {
    fn full_exhaustive
        (f: Rc<dyn Fn((BigInt, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>,
          d: Natural) -> Option<(bool, List<Term>)> {
        <Natural as FullExhaustive>::full_exhaustive(
            (({
                let f_cap = f.clone();
                Rc::new(move |(x, _): (Natural, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
                    (*f_cap)((
                        nat_of_natural(x.clone()),
                        (({
                            let x_cap = x.clone();
                            Rc::new(move |_: Unit| -> Term {
                                <BigInt as TermOf>::term_of(nat_of_natural(x_cap.clone()))
                            })
                        }) as Rc<dyn Fn(Unit) -> Term>)
                    ))
                })
            }) as Rc<dyn Fn((Natural, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
            d.clone()
        )
    }
}

pub trait FullExhaustive : TermOf {
    fn full_exhaustive (x0: Rc<dyn Fn((Self, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>,
                        x1: Natural) -> Option<(bool, List<Term>)> where Self: Sized;
}
