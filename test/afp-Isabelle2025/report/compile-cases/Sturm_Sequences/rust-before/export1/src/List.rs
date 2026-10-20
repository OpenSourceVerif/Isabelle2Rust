use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::One;
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
                    nth(xs.clone(), (match (n.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }))
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

pub fn rev <A> (xs: List<A>) -> List<A>
where
    A : Clone + 'static
{
    fold(((Rc::new(move |a: A, b: List<A>| -> List<A> {
        List::Cons (a.clone(), Box::new(b.clone()))
    })) as Rc<dyn Fn(A, List<A>) -> List<A>>), xs.clone(), List::Nil)
}

pub fn null <A> (x0: List<A>) -> bool
where
    A : Clone + 'static
{
    match x0 {
        List::Nil =>
            true,
        List::Cons (_, _) =>
            false,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn last <A> (x0: List<A>) -> A
where
    A : Clone + 'static
{
    match x0 {
        List::Cons (x, p0) =>
            {
                let xs = *p0;
                if null(xs.clone()) {
                    x.clone()
                } else {
                    last(xs.clone())
                }
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

pub fn hd <A> (x0: List<A>) -> A
where
    A : Clone + 'static
{
    match x0 {
        List::Cons (x21, _) =>
            x21.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn tl <A> (x0: List<A>) -> List<A>
where
    A : Clone + 'static
{
    match x0 {
        List::Nil =>
            List::Nil,
        List::Cons (_, p0) =>
            {
                let x22 = *p0;
                x22.clone()
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

pub fn drop_while <A> (p: Rc<dyn Fn(A) -> bool>, x1: List<A>) -> List<A>
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
                    drop_while(p.clone(), xs.clone())
                } else {
                    List::Cons (x.clone(), Box::new(xs.clone()))
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

pub fn remdups_adj <A> (x0: List<A>) -> List<A>
where
    A : Clone + Equal + 'static
{
    match x0 {
        List::Nil =>
            List::Nil,
        List::Cons (x, p0a) =>
            match *p0a {
                List::Nil =>
                    List::Cons (x.clone(), Box::new(List::Nil)),
                List::Cons (y, p1a) =>
                    {
                        let xs = *p1a;
                        if eq(x.clone(), y.clone()) {
                            remdups_adj(List::Cons (x.clone(), Box::new(xs.clone())))
                        } else {
                            List::Cons (x.clone(), Box::new(remdups_adj(List::Cons (y.clone(), Box::new(xs.clone())))))
                        }
                    },
                _ =>
                    panic!("non-exhaustive match")
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

impl <A : Clone + Equal + 'static> Equal for List<A> {
    fn equal (x0: List<A>, x1: List<A>) -> bool {
        match (x0, x1) {
            (List::Nil, List::Cons (_, _)) =>
                false,
            (List::Cons (_, _), List::Nil) =>
                false,
            (List::Cons (x21, p0), List::Cons (y21, p1)) =>
                {
                    let x22 = *p0;
                    let y22 = *p1;
                    eq(x21.clone(), y21.clone()) &&
                      <List<A> as Equal>::equal(x22.clone(), y22.clone())
                },
            (List::Nil, List::Nil) =>
                true,
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
