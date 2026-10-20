use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Fun::comp;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::Lattices_Big::max;
use crate::List::List;
use crate::List::map_filter;
use crate::List::mapa;
use crate::List::maps;
use crate::List::nth;
use crate::List::size_list;
use crate::List::upt;
use crate::List::zip;
use crate::Option::Option;
use crate::Orderings::Linorder;
use crate::Orderings::Ord;
use crate::Product_Type::fst;
use crate::Product_Type::snd;
use crate::Set::Set;
use crate::Set::filter;
use crate::Set::image;

use std::rc::Rc;

pub fn argmax <A, B> (f: Rc<dyn Fn(A) -> B>, a: Set<A>) -> Set<A>
where
    A : Clone + 'static,
    B : Clone + Equal + Linorder + 'static
{
    filter(
        (({
            let a_cap = a.clone();
            let f_cap = f.clone();
            Rc::new(move |x: A| -> bool {
                eq((*f_cap)(x.clone()), max(image(f_cap.clone(), a_cap.clone())))
            })
        }) as Rc<dyn Fn(A) -> bool>),
        a.clone()
    )
}

pub fn filterpositions2 <A>
    (p: Rc<dyn Fn(A) -> bool>, l: List<A>) -> List<BigInt>
where
    A : Clone + 'static
{
    maps(
        (({
            let l_cap = l.clone();
            let p_cap = p.clone();
            Rc::new(move |n: BigInt| -> List<BigInt> {
                if (*p_cap)(nth(l_cap.clone(), n.clone())) {
                    List::Cons (n.clone(), Box::new(List::Nil))
                } else {
                    List::Nil
                }
            })
        }) as Rc<dyn Fn(BigInt) -> List<BigInt>>),
        upt(BigInt::ZERO, size_list(l.clone()))
    )
}

pub fn maxpositions <A> (l: List<A>) -> List<BigInt>
where
    A : Clone + Linorder + 'static
{
    filterpositions2((({
        let l_cap = l.clone();
        Rc::new(move |a: A| -> bool {
            <A as Ord>::less_eq(max(Set::Set (l_cap.clone())), a.clone())
        })
    }) as Rc<dyn Fn(A) -> bool>), l.clone())
}

pub fn argmax_list <A, B> (f: Rc<dyn Fn(A) -> B>, l: List<A>) -> List<A>
where
    A : Clone + 'static,
    B : Clone + Linorder + 'static
{
    mapa((({
        let l_cap = l.clone();
        Rc::new(move |a: BigInt| -> A {
            nth(l_cap.clone(), a.clone())
        })
    }) as Rc<dyn Fn(BigInt) -> A>), maxpositions(mapa(f.clone(), l.clone())))
}

pub fn filterpositions <A>
    (p: Rc<dyn Fn(A) -> bool>, l: List<A>) -> List<BigInt>
where
    A : Clone + 'static
{
    map_filter(
        (({
            let p_cap = p.clone();
            Rc::new(move |x: (A, BigInt)| -> Option<BigInt> {
                if (*comp(p_cap.clone(), ((Rc::new(move |a: (A, BigInt)| -> A {
                    fst(a.clone())
                })) as Rc<dyn Fn((A, BigInt)) -> A>)))(x.clone()) {
                    Option::Some (snd(x.clone()))
                } else {
                    Option::None
                }
            })
        }) as Rc<dyn Fn((A, BigInt)) -> Option<BigInt>>),
        zip(l.clone(), upt(BigInt::ZERO, size_list(l.clone())))
    )
}
