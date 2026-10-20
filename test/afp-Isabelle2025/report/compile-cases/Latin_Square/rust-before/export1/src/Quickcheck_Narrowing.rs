use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::List::List;
use crate::List::append;

use std::rc::Rc;

#[derive(Clone)]
pub enum NarrowingType {
    NarrowingSumOfProducts (Box<List<List<NarrowingType>>>)
}

#[derive(Clone)]
pub enum NarrowingTerm {
    NarrowingVariable (List<BigInt>, NarrowingType),
    NarrowingConstructor (BigInt, Box<List<NarrowingTerm>>)
}

#[derive(Clone)]
pub enum NarrowingCons<A> {
    NarrowingCons (NarrowingType, List<Rc<dyn Fn(List<NarrowingTerm>) -> A>>)
}

pub fn sum <A>
    (a: Rc<dyn Fn(BigInt) -> NarrowingCons<A>>,
      b: Rc<dyn Fn(BigInt) -> NarrowingCons<A>>, d: BigInt) -> NarrowingCons<A>
where
    A : Clone + 'static
{
    match (*a)(d.clone()) {
        NarrowingCons::NarrowingCons (NarrowingType::NarrowingSumOfProducts (p0), ca) =>
            {
                let ssa = *p0;
                match (*b)(d.clone()) {
                    NarrowingCons::NarrowingCons (NarrowingType::NarrowingSumOfProducts (p0), cb) =>
                        {
                            let ssb = *p0;
                            NarrowingCons::NarrowingCons (NarrowingType::NarrowingSumOfProducts (Box::new(append(ssa.clone(), ssb.clone()))), append(ca.clone(), cb.clone()))
                        },
                    _ =>
                        panic!("non-exhaustive match")
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn cons <A> (a: A, x1: BigInt) -> NarrowingCons<A>
where
    A : Clone + 'static
{
    NarrowingCons::NarrowingCons (NarrowingType::NarrowingSumOfProducts (Box::new(List::Cons (List::Nil, Box::new(List::Nil)))), List::Cons (
        (({
            let a_cap = a.clone();
            Rc::new(move |_: List<NarrowingTerm>| -> A {
                a_cap.clone()
            })
        }) as Rc<dyn Fn(List<NarrowingTerm>) -> A>),
        Box::new(List::Nil)
    ))
}
