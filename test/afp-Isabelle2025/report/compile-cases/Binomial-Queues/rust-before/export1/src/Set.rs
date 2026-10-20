use crate::HOL::Equal;
use crate::List::List;
use crate::List::filter;
use crate::List::fold;
use crate::List::mapa;
use crate::List::remove_all;

use std::rc::Rc;

#[derive(Clone)]
pub enum Set<A> {
    Set (List<A>),
    Coset (List<A>)
}

pub fn image <B, A> (f: Rc<dyn Fn(A) -> B>, x1: Set<A>) -> Set<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (f, Set::Set (xs)) =>
            Set::Set (mapa(f.clone(), xs.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn insert <A> (x: A, xa1: Set<A>) -> Set<A>
where
    A : Clone + Equal + 'static
{
    match (x, xa1) {
        (x, Set::Coset (xs)) =>
            Set::Coset (remove_all(x.clone(), xs.clone())),
        (x, Set::Set (xs)) =>
            Set::Set (crate::List::insert(x.clone(), xs.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn member <A> (x: A, xa1: Set<A>) -> bool
where
    A : Clone + Equal + 'static
{
    match (x, xa1) {
        (x, Set::Coset (xs)) =>
            ! crate::List::member(xs.clone(), x.clone()),
        (x, Set::Set (xs)) =>
            crate::List::member(xs.clone(), x.clone()),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn bot_set <A> () -> Set<A>
where
    A : Clone + 'static
{
    Set::Set (List::Nil)
}

pub fn sup_set <A> (x0: Set<A>, a: Set<A>) -> Set<A>
where
    A : Clone + Equal + 'static
{
    match (x0, a) {
        (Set::Coset (xs), a) =>
            Set::Coset (filter(
                (({
                    let a_cap = a.clone();
                    Rc::new(move |x: A| -> bool {
                        ! member(x.clone(), a_cap.clone())
                    })
                }) as Rc<dyn Fn(A) -> bool>),
                xs.clone()
            )),
        (Set::Set (xs), a) =>
            fold(((Rc::new(move |aa: A, b: Set<A>| -> Set<A> {
                insert(aa.clone(), b.clone())
            })) as Rc<dyn Fn(A, Set<A>) -> Set<A>>), xs.clone(), a.clone()),
        _ =>
            panic!("non-exhaustive match")
    }
}
