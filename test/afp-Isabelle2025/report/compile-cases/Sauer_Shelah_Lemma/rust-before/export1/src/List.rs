use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::suc;
use crate::HOL::Equal;
use crate::HOL::eq;

use std::rc::Rc;

#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons (A, Box<List<A>>)
}

pub fn fold <B, A> (f: Rc<dyn Fn(A, B) -> B>, x1: List<A>, s: B) -> B
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1, s) {
        (f, List::Cons (x, p0), s) =>
            {
                let xs = *p0;
                fold(f.clone(), xs.clone(), (*f)(x.clone(), s.clone()))
            },
        (_, List::Nil, s) =>
            s.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn append <A> (x0: List<A>, ys: List<A>) -> List<A>
where
    A : Clone + 'static
{
    match (x0, ys) {
        (List::Nil, ys) =>
            ys.clone(),
        (List::Cons (x, p0), ys) =>
            {
                let xs = *p0;
                List::Cons (x.clone(), Box::new(append(xs.clone(), ys.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn filter <A> (p: Rc<dyn Fn(A) -> bool>, x1: List<A>) -> List<A>
where
    A : Clone + 'static
{
    match (p, x1) {
        (_, List::Nil) =>
            List::Nil,
        (p, List::Cons (x, p0)) =>
            {
                let xs = *p0;
                if (*p)(x.clone()) {
                    List::Cons (x.clone(), Box::new(filter(p.clone(), xs.clone())))
                } else {
                    filter(p.clone(), xs.clone())
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn member <A> (x0: List<A>, y: A) -> bool
where
    A : Clone + Equal + 'static
{
    match (x0, y) {
        (List::Nil, _) =>
            false,
        (List::Cons (x, p0), y) =>
            {
                let xs = *p0;
                eq(x.clone(), y.clone()) || member(xs.clone(), y.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn insert <A> (x: A, xs: List<A>) -> List<A>
where
    A : Clone + Equal + 'static
{
    if member(xs.clone(), x.clone()) {
        xs.clone()
    } else {
        List::Cons (x.clone(), Box::new(xs.clone()))
    }
}

pub fn list_ex <A> (p: Rc<dyn Fn(A) -> bool>, x1: List<A>) -> bool
where
    A : Clone + 'static
{
    match (p, x1) {
        (_, List::Nil) =>
            false,
        (p, List::Cons (x, p0)) =>
            {
                let xs = *p0;
                (*p)(x.clone()) || list_ex(p.clone(), xs.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn remdups <A> (x0: List<A>) -> List<A>
where
    A : Clone + Equal + 'static
{
    match x0 {
        List::Nil =>
            List::Nil,
        List::Cons (x, p0) =>
            {
                let xs = *p0;
                if member(xs.clone(), x.clone()) {
                    remdups(xs.clone())
                } else {
                    List::Cons (x.clone(), Box::new(remdups(xs.clone())))
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn mapa <B, A> (f: Rc<dyn Fn(A) -> B>, x1: List<A>) -> List<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (_, List::Nil) =>
            List::Nil,
        (f, List::Cons (x21, p0)) =>
            {
                let x22 = *p0;
                List::Cons ((*f)(x21.clone()), Box::new(mapa(f.clone(), x22.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn subseqs <A> (x0: List<A>) -> List<List<A>>
where
    A : Clone + 'static
{
    match x0 {
        List::Nil =>
            List::Cons (List::Nil, Box::new(List::Nil)),
        List::Cons (x, p0) =>
            {
                let xs = *p0;
                {
                    let xss = subseqs(xs.clone());
                    append(mapa((({
                        let x_cap = x.clone();
                        Rc::new(move |a: List<A>| -> List<A> {
                            List::Cons (x_cap.clone(), Box::new(a.clone()))
                        })
                    }) as Rc<dyn Fn(List<A>) -> List<A>>), xss.clone()), xss.clone())
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn remove_all <A> (x: A, xa1: List<A>) -> List<A>
where
    A : Clone + Equal + 'static
{
    match (x, xa1) {
        (_, List::Nil) =>
            List::Nil,
        (x, List::Cons (y, p0)) =>
            {
                let xs = *p0;
                if eq(x.clone(), y.clone()) {
                    remove_all(x.clone(), xs.clone())
                } else {
                    List::Cons (y.clone(), Box::new(remove_all(x.clone(), xs.clone())))
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn gen_length <A> (n: BigInt, x1: List<A>) -> BigInt
where
    A : Clone + 'static
{
    match (n, x1) {
        (n, List::Cons (_, p0)) =>
            {
                let xs = *p0;
                gen_length(suc(n.clone()), xs.clone())
            },
        (n, List::Nil) =>
            n.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn list_all <A> (p: Rc<dyn Fn(A) -> bool>, x1: List<A>) -> bool
where
    A : Clone + 'static
{
    match (p, x1) {
        (_, List::Nil) =>
            true,
        (p, List::Cons (x, p0)) =>
            {
                let xs = *p0;
                (*p)(x.clone()) && list_all(p.clone(), xs.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_list <A> (x: List<A>) -> BigInt
where
    A : Clone + 'static
{
    gen_length(BigInt::ZERO, x.clone())
}
