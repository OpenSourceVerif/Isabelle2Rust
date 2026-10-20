use crate::HOL::Equal;
use crate::List::map_project;
use crate::Option::Option;
use crate::Product_Type::fst;
use crate::Product_Type::snd;
use crate::Set::Set;
use crate::Set::member;

use std::rc::Rc;

pub fn image <B, A> (r: Set<(A, B)>, s: Set<A>) -> Set<B>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    map_project(
        (({
            let s_cap = s.clone();
            Rc::new(move |(x, y): (A, B)| -> Option<B> {
                if member(x.clone(), s_cap.clone()) {
                    Option::Some (y.clone())
                } else {
                    Option::None
                }
            })
        }) as Rc<dyn Fn((A, B)) -> Option<B>>),
        r.clone()
    )
}

pub fn rangea <B, A> (r: Set<(A, B)>) -> Set<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    crate::Set::image(((Rc::new(move |a: (A, B)| -> B {
        snd(a.clone())
    })) as Rc<dyn Fn((A, B)) -> B>), r.clone())
}

pub fn domain <A, B> (r: Set<(A, B)>) -> Set<A>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    crate::Set::image(((Rc::new(move |a: (A, B)| -> A {
        fst(a.clone())
    })) as Rc<dyn Fn((A, B)) -> A>), r.clone())
}

pub fn converse <A, B> (r: Set<(A, B)>) -> Set<(B, A)>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    crate::Set::image(
        ((Rc::new(move |(x, y): (A, B)| -> (B, A) {
            (y.clone(), x.clone())
        })) as Rc<dyn Fn((A, B)) -> (B, A)>),
        r.clone()
    )
}
