use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::One;
use crate::Arith::funpow;
use crate::Arith::suc;
use crate::Fun::comp;
use crate::Fun::id;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::Option::Option;
use crate::Orderings::Linorder;
use crate::Orderings::Ord;
use crate::Set::Set;

use std::rc::Rc;

#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons (A, Box<List<A>>)
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

pub fn upt (i: BigInt, j: BigInt) -> List<BigInt> {
    if i.clone() < j.clone() {
        List::Cons (i.clone(), Box::new(upt(suc(i.clone()), j.clone())))
    } else {
        List::Nil
    }
}

pub fn zip <B, A> (x0: List<A>, x1: List<B>) -> List<(A, B)>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (x0, x1) {
        (List::Cons (x, p0), List::Cons (y, p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                List::Cons ((x.clone(), y.clone()), Box::new(zip(xs.clone(), ys.clone())))
            },
        (_, List::Nil) =>
            List::Nil,
        (List::Nil, _) =>
            List::Nil,
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

pub fn rotate1 <A> (x0: List<A>) -> List<A>
where
    A : Clone + 'static
{
    match x0 {
        List::Nil =>
            List::Nil,
        List::Cons (x, p0) =>
            {
                let xs = *p0;
                append(xs.clone(), List::Cons (x.clone(), Box::new(List::Nil)))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rotate <A> (n: BigInt) -> Rc<dyn Fn(List<A>) -> List<A>>
where
    A : Clone + 'static
{
    (({
        let n_cap = n.clone();
        Rc::new(move |a: List<A>| -> List<A> {
            (*funpow(n_cap.clone(), ((Rc::new(move |aa: List<A>| -> List<A> {
                rotate1(aa.clone())
            })) as Rc<dyn Fn(List<A>) -> List<A>>)))(a.clone())
        })
    }) as Rc<dyn Fn(List<A>) -> List<A>>)
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

pub fn product <B, A> (x0: List<A>, ys: List<B>) -> List<(A, B)>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (x0, ys) {
        (List::Nil, _) =>
            List::Nil,
        (List::Cons (x, p0), ys) =>
            {
                let xs = *p0;
                append(mapa((({
                    let x_cap = x.clone();
                    Rc::new(move |a: B| -> (A, B) {
                        (x_cap.clone(), a.clone())
                    })
                }) as Rc<dyn Fn(B) -> (A, B)>), ys.clone()), product(xs.clone(), ys.clone()))
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

pub fn remove1 <A> (x: A, xa1: List<A>) -> List<A>
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
                    xs.clone()
                } else {
                    List::Cons (y.clone(), Box::new(remove1(x.clone(), xs.clone())))
                }
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

pub fn map_filter <B, A> (f: Rc<dyn Fn(A) -> Option<B>>, x1: List<A>) -> List<B>
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
                match (*f)(x.clone()) {
                    Option::None =>
                        map_filter(f.clone(), xs.clone()),
                    Option::Some (y) =>
                        List::Cons (y.clone(), Box::new(map_filter(f.clone(), xs.clone()))),
                    _ =>
                        panic!("non-exhaustive match")
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn map_project <B, A> (f: Rc<dyn Fn(A) -> Option<B>>, x1: Set<A>) -> Set<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (f, Set::Set (xs)) =>
            Set::Set (map_filter(f.clone(), xs.clone())),
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

pub fn insort_key <A, B> (f: Rc<dyn Fn(A) -> B>, x: A, xa2: List<A>) -> List<A>
where
    A : Clone + 'static,
    B : Clone + Linorder + 'static
{
    match (f, x, xa2) {
        (_, x, List::Nil) =>
            List::Cons (x.clone(), Box::new(List::Nil)),
        (f, x, List::Cons (y, p0)) =>
            {
                let ys = *p0;
                if <B as Ord>::less_eq((*f)(x.clone()), (*f)(y.clone())) {
                    List::Cons (x.clone(), Box::new(List::Cons (y.clone(), Box::new(ys.clone()))))
                } else {
                    List::Cons (y.clone(), Box::new(insort_key(f.clone(), x.clone(), ys.clone())))
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn sort_key <A, B> (f: Rc<dyn Fn(A) -> B>, xs: List<A>) -> List<A>
where
    A : Clone + 'static,
    B : Clone + Linorder + 'static
{
    (*foldr((({
        let f_cap = f.clone();
        Rc::new(move |a: A, b: List<A>| -> List<A> {
            insort_key(f_cap.clone(), a.clone(), b.clone())
        })
    }) as Rc<dyn Fn(A, List<A>) -> List<A>>), xs.clone()))(List::Nil)
}

pub fn size_list <A> (x: List<A>) -> BigInt
where
    A : Clone + 'static
{
    gen_length(BigInt::ZERO, x.clone())
}

pub fn sorted_list_of_set <A> (x0: Set<A>) -> List<A>
where
    A : Clone + Equal + Linorder + 'static
{
    match x0 {
        Set::Set (xs) =>
            sort_key(
                ((Rc::new(move |x: A| -> A {
                    x.clone()
                })) as Rc<dyn Fn(A) -> A>),
                remdups(xs.clone())
            ),
        _ =>
            panic!("non-exhaustive match")
    }
}
