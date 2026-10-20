use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::one_nat;
use crate::Arith::suc;
use crate::HOL::Equal;
use crate::HOL::eq;

use std::rc::Rc;

#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons (A, Box<List<A>>)
}

pub fn nth <A> (x0: List<A>, n: BigInt) -> A
where
    A : Clone + 'static
{
    match (x0, n) {
        (List::Cons (x, p0), n) =>
            {
                let xs = *p0;
                if n.clone() == BigInt::ZERO {
                    x.clone()
                } else {
                    nth(xs.clone(), (match (n.clone().clone(), one_nat().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }))
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn upt (i: BigInt, j: BigInt) -> List<BigInt> {
    if i.clone() < j.clone() {
        List::Cons (i.clone(), Box::new(upt(suc(i.clone()), j.clone())))
    } else {
        List::Nil
    }
}

pub fn drop <A> (n: BigInt, x1: List<A>) -> List<A>
where
    A : Clone + 'static
{
    match (n, x1) {
        (_, List::Nil) =>
            List::Nil,
        (n, List::Cons (x, p0)) =>
            {
                let xs = *p0;
                if n.clone() == BigInt::ZERO {
                    List::Cons (x.clone(), Box::new(xs.clone()))
                } else {
                    drop((match (n.clone().clone(), one_nat().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }), xs.clone())
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
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

pub fn maps <B, A> (f: Rc<dyn Fn(A) -> List<B>>, x1: List<A>) -> List<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (_, List::Nil) =>
            List::Nil,
        (f, List::Cons (x, p0)) =>
            {
                let xs = *p0;
                append((*f)(x.clone()), maps(f.clone(), xs.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn take <A> (n: BigInt, x1: List<A>) -> List<A>
where
    A : Clone + 'static
{
    match (n, x1) {
        (_, List::Nil) =>
            List::Nil,
        (n, List::Cons (x, p0)) =>
            {
                let xs = *p0;
                if n.clone() == BigInt::ZERO {
                    List::Nil
                } else {
                    List::Cons (x.clone(), Box::new(take((match (n.clone().clone(), one_nat().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }), xs.clone())))
                }
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

pub fn size_list <A> (x: List<A>) -> BigInt
where
    A : Clone + 'static
{
    gen_length(BigInt::ZERO, x.clone())
}
