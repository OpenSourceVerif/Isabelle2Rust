use crate::HOL::Equal;
use crate::List::List;
use crate::List::list_all;
use crate::List::mapa;
use crate::Orderings::Ord;

use std::rc::Rc;

#[derive(Clone)]
pub enum Set<A> {
    Set (List<A>),
    Coset (List<A>)
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

impl <A : Clone + Equal + 'static> Ord for Set<A> {
    fn less_eq (a: Set<A>, b: Set<A>) -> bool {
        match (a, b) {
            (Set::Coset (List::Nil), Set::Set (List::Nil)) =>
                false,
            (a, Set::Coset (ys)) =>
                list_all(
                    (({
                        let a_cap = a.clone();
                        Rc::new(move |y: A| -> bool {
                            ! member(y.clone(), a_cap.clone())
                        })
                    }) as Rc<dyn Fn(A) -> bool>),
                    ys.clone()
                ),
            (Set::Set (xs), b) =>
                list_all(
                    (({
                        let b_cap = b.clone();
                        Rc::new(move |x: A| -> bool {
                            member(x.clone(), b_cap.clone())
                        })
                    }) as Rc<dyn Fn(A) -> bool>),
                    xs.clone()
                ),
            _ =>
                panic!("non-exhaustive match")
        }
    }
    fn less (x0: Self,
             x1: Self) -> bool { panic!("unimplemented instance method: less") }
}

impl <A : Clone + Equal + 'static> Equal for Set<A> {
    fn equal (a: Set<A>, b: Set<A>) -> bool {
        <Set<A> as Ord>::less_eq(a.clone(), b.clone()) &&
          <Set<A> as Ord>::less_eq(b.clone(), a.clone())
    }
}

pub fn ball <A> (x0: Set<A>, p: Rc<dyn Fn(A) -> bool>) -> bool
where
    A : Clone + 'static
{
    match (x0, p) {
        (Set::Set (xs), p) =>
            list_all(p.clone(), xs.clone()),
        _ =>
            panic!("non-exhaustive match")
    }
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
