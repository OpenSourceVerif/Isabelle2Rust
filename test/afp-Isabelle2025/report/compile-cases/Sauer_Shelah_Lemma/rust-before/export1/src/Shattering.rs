use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Conditionally_Complete_Lattices::sup_nat;
use crate::Enum::Enum;
use crate::Finite_Set::card;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::Set::Set;
use crate::Set::collect;
use crate::Set::image;
use crate::Set::inf_set;
use crate::Set::pow;

use std::rc::Rc;

pub fn vc_dim <A> (f: Set<Set<A>>) -> BigInt
where
    A : Clone + Enum + Equal + 'static
{
    sup_nat(image(((Rc::new(move |a: Set<A>| -> BigInt {
        card(a.clone())
    })) as Rc<dyn Fn(Set<A>) -> BigInt>), collect(
        (({
            let f_cap = f.clone();
            Rc::new(move |s: Set<A>| -> bool {
                eq(image((({
                    let s_cap = s.clone();
                    Rc::new(move |a: Set<A>| -> Set<A> {
                        inf_set(s_cap.clone(), a.clone())
                    })
                }) as Rc<dyn Fn(Set<A>) -> Set<A>>), f_cap.clone()), pow(s.clone()))
            })
        }) as Rc<dyn Fn(Set<A>) -> bool>)
    )))
}

pub fn shattered_by <A> (f: Set<Set<A>>) -> Set<Set<A>>
where
    A : Clone + Enum + Equal + 'static
{
    collect(
        (({
            let f_cap = f.clone();
            Rc::new(move |a: Set<A>| -> bool {
                eq(image((({
                    let a_cap = a.clone();
                    Rc::new(move |b: Set<A>| -> Set<A> {
                        inf_set(a_cap.clone(), b.clone())
                    })
                }) as Rc<dyn Fn(Set<A>) -> Set<A>>), f_cap.clone()), pow(a.clone()))
            })
        }) as Rc<dyn Fn(Set<A>) -> bool>)
    )
}
