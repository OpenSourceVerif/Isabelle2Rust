use crate::Binomial_Queue::Bintree;
use crate::HOL::Equal;
use crate::List::List;
use crate::List::append;
use crate::Option::Option;
use crate::Orderings::Linorder;
use crate::PQ::Pq;
use crate::PQ::empty;
use crate::PQ::push;

use std::rc::Rc;

pub fn bt_dfs <C, B, A>
    (f: Rc<dyn Fn(Bintree<A, B>) -> C>, x1: Bintree<A, B>) -> List<C>
where
    A : Clone + Linorder + 'static,
    B : Clone + 'static,
    C : Clone + 'static
{
    match (f, x1) {
        (f, Bintree::Node (a, v, p0)) =>
            {
                let ts = *p0;
                List::Cons ((*f)(Bintree::Node (a.clone(), v.clone(), Box::new(ts.clone()))), Box::new(bts_dfs(f.clone(), ts.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn bts_dfs <C, B, A>
    (f: Rc<dyn Fn(Bintree<A, B>) -> C>, x1: List<Bintree<A, B>>) -> List<C>
where
    A : Clone + Linorder + 'static,
    B : Clone + 'static,
    C : Clone + 'static
{
    match (f, x1) {
        (_, List::Nil) =>
            List::Nil,
        (f, List::Cons (t, p0)) =>
            {
                let ts = *p0;
                append(bt_dfs(f.clone(), t.clone()), bts_dfs(f.clone(), ts.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn dfs <C, B, A>
    (f: Rc<dyn Fn(Bintree<A, B>) -> C>,
      x1: List<Option<Bintree<A, B>>>) -> List<C>
where
    A : Clone + Linorder + 'static,
    B : Clone + 'static,
    C : Clone + 'static
{
    match (f, x1) {
        (_, List::Nil) =>
            List::Nil,
        (f, List::Cons (Option::None, p0)) =>
            {
                let xs = *p0;
                dfs(f.clone(), xs.clone())
            },
        (f, List::Cons (Option::Some (t), p0)) =>
            {
                let xs = *p0;
                append(bt_dfs(f.clone(), t.clone()), dfs(f.clone(), xs.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn alist <A, B> (x0: Bintree<A, B>) -> (B, A)
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        Bintree::Node (a, v, _) =>
            (v.clone(), a.clone()),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn bt_augment <A, B> (x0: Bintree<A, B>, q: Pq<B, A>) -> Pq<B, A>
where
    A : Clone + Linorder + 'static,
    B : Clone + Equal + 'static
{
    match (x0, q) {
        (Bintree::Node (a, v, p0), q) =>
            {
                let ts = *p0;
                push(v.clone(), a.clone(), bts_augment(ts.clone(), q.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn bts_augment <A, B> (x0: List<Bintree<A, B>>, q: Pq<B, A>) -> Pq<B, A>
where
    A : Clone + Linorder + 'static,
    B : Clone + Equal + 'static
{
    match (x0, q) {
        (List::Nil, q) =>
            q.clone(),
        (List::Cons (t, p0), q) =>
            {
                let ts = *p0;
                bts_augment(ts.clone(), bt_augment(t.clone(), q.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn pqueue <A, B> (x0: List<Option<Bintree<A, B>>>) -> Pq<B, A>
where
    A : Clone + Linorder + 'static,
    B : Clone + Equal + 'static
{
    match x0 {
        List::Nil =>
            empty::<A, B>(),
        List::Cons (Option::None, p0) =>
            {
                let xs = *p0;
                pqueue(xs.clone())
            },
        List::Cons (Option::Some (t), p0) =>
            {
                let xs = *p0;
                bt_augment(t.clone(), pqueue(xs.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}
