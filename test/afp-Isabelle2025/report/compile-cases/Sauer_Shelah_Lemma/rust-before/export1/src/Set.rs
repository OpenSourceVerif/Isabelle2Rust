use crate::Enum::Enum;
use crate::HOL::Equal;
use crate::List::List;
use crate::List::filter;
use crate::List::fold;
use crate::List::list_all;
use crate::List::mapa;
use crate::List::remove_all;
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

pub fn bot_set <A> () -> Set<A>
where
    A : Clone + 'static
{
    Set::Set (List::Nil)
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

pub fn pow <A> (x0: Set<A>) -> Set<Set<A>>
where
    A : Clone + Equal + 'static
{
    match x0 {
        Set::Set (List::Cons (x, p0)) =>
            {
                let xs = *p0;
                {
                    let a = pow(Set::Set (xs.clone()));
                    sup_set(a.clone(), image((({
                        let x_cap = x.clone();
                        Rc::new(move |aa: Set<A>| -> Set<A> {
                            insert(x_cap.clone(), aa.clone())
                        })
                    }) as Rc<dyn Fn(Set<A>) -> Set<A>>), a.clone()))
                }
            },
        Set::Set (List::Nil) =>
            insert(bot_set::<A>(), bot_set::<Set<A>>()),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn remove <A> (x: A, xa1: Set<A>) -> Set<A>
where
    A : Clone + Equal + 'static
{
    match (x, xa1) {
        (x, Set::Coset (xs)) =>
            Set::Coset (crate::List::insert(x.clone(), xs.clone())),
        (x, Set::Set (xs)) =>
            Set::Set (remove_all(x.clone(), xs.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn collect <A> (p: Rc<dyn Fn(A) -> bool>) -> Set<A>
where
    A : Clone + Enum + 'static
{
    Set::Set (filter(p.clone(), <A as Enum>::enuma()))
}

pub fn inf_set <A> (a: Set<A>, x1: Set<A>) -> Set<A>
where
    A : Clone + Equal + 'static
{
    match (a, x1) {
        (a, Set::Coset (xs)) =>
            fold(((Rc::new(move |aa: A, b: Set<A>| -> Set<A> {
                remove(aa.clone(), b.clone())
            })) as Rc<dyn Fn(A, Set<A>) -> Set<A>>), xs.clone(), a.clone()),
        (a, Set::Set (xs)) =>
            Set::Set (filter(
                (({
                    let a_cap = a.clone();
                    Rc::new(move |x: A| -> bool {
                        member(x.clone(), a_cap.clone())
                    })
                }) as Rc<dyn Fn(A) -> bool>),
                xs.clone()
            )),
        _ =>
            panic!("non-exhaustive match")
    }
}
