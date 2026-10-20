use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::suc;
use crate::Fun::comp;
use crate::Fun::id;
use crate::HOL::Equal;
use crate::HOL::eq;

use std::rc::Rc;

#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons (A, Box<List<A>>)
}

pub fn upt (i: BigInt, j: BigInt) -> List<BigInt> {
    if i.clone() < j.clone() {
        List::Cons (i.clone(), Box::new(upt(suc(i.clone()), j.clone())))
    } else {
        List::Nil
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

pub fn foldr <B, A>
    (f: Rc<dyn Fn(A, B) -> B>, x1: List<A>) -> Rc<dyn Fn(B) -> B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (_, List::Nil) =>
            ((Rc::new(move |a: B| -> B {
                id(a.clone())
            })) as Rc<dyn Fn(B) -> B>),
        (f, List::Cons (x, p0)) =>
            {
                let xs = *p0;
                (({
                    let xs_cap = xs.clone();
                    let x_cap = x.clone();
                    let f_cap = f.clone();
                    Rc::new(move |a: B| -> B {
                        (*comp((({
                            let x_capa = x_cap.clone();
                            let f_capa = f_cap.clone();
                            Rc::new(move |b: B| -> B {
                                (*f_capa)(x_capa.clone(), b.clone())
                            })
                        }) as Rc<dyn Fn(B) -> B>), (({
                            let xs_capa = xs_cap.clone();
                            let f_capa = f_cap.clone();
                            Rc::new(move |aa: B| -> B {
                                (*foldr(f_capa.clone(), xs_capa.clone()))(aa.clone())
                            })
                        }) as Rc<dyn Fn(B) -> B>)))(a.clone())
                    })
                }) as Rc<dyn Fn(B) -> B>)
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
