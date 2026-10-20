use crate::HOL::Equal;
use crate::Product_Type::fst;
use crate::Product_Type::snd;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::insert;

use std::rc::Rc;

pub fn fsts <A, B> () -> Rc<dyn Fn((A, B)) -> Set<A>>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    Rc::new(move |p: (A, B)| -> Set<A> {
        insert(fst(p.clone()), bot_set::<A>())
    })
}

pub fn snds <B, A> () -> Rc<dyn Fn((A, B)) -> Set<B>>
where
    A : Clone + 'static,
    B : Clone + Equal + 'static
{
    Rc::new(move |p: (A, B)| -> Set<B> {
        insert(snd(p.clone()), bot_set::<B>())
    })
}

pub fn rel_prod <D, B, C, A>
    (r1: Rc<dyn Fn(A, B) -> bool>, r2: Rc<dyn Fn(C, D) -> bool>, x2: (A, C),
      x3: (B, D)) -> bool
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static,
    D : Clone + 'static
{
    match (r1, r2, x2, x3) {
        (r1, r2, (a, b), (c, d)) =>
            (*r1)(a.clone(), c.clone()) && (*r2)(b.clone(), d.clone()),
        _ =>
            panic!("non-exhaustive match")
    }
}
