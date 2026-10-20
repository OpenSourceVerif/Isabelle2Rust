use num_bigint::*;

use num_traits::sign::Signed as _;

use crate::Arith::one_nat;
use crate::Arith::suc;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::rev;
use crate::List::size_list;

use std::rc::Rc;

pub fn find_index<A>(p: Rc<dyn Fn(A) -> bool>, x1: List<A>) -> BigInt
where
    A: Clone + 'static
{
    match (p, x1) {
        (_, List::Nil) => {
            BigInt::ZERO
        },
        (p, List::Cons(x, p0)) => {
            let xs = *p0;
            if (*p)(x) {
                BigInt::ZERO
            } else {
                find_index(p, xs) + one_nat()
            }
        },
    }
}

pub fn index<A>(xs: List<A>) -> Rc<dyn Fn(A) -> BigInt>
where
    A: Clone + Equal + 'static
{
    Rc::new(move |a: A| -> BigInt {
        find_index(({
            Rc::new(move |x: A| -> bool {
                eq(x, a.clone())
            })
        }) as Rc<dyn Fn(A) -> bool>, xs.clone())
    })
}

// borrow-optimized by shared parameters
pub fn insert_nth<A>(n: &BigInt, x: A, xs: List<A>) -> List<A>
where
    A: Clone + 'static
{
    if n.clone() == BigInt::ZERO {
        List::Cons(x, Box::new(xs))
    } else {
        match xs {
            List::Nil => {
                List::Cons(x, Box::new(List::Nil))
            },
            List::Cons(y, p0) => {
                let ys = *p0;
                List::Cons(y, Box::new(insert_nth(&({
                    let (m, n) = (n.clone().clone(), one_nat().clone());
                    if m <= n {
                        BigInt::ZERO
                    } else {
                        m - n
                    }
                }), x, ys)))
            },
        }
    }
}

// borrow-optimized by shared parameters
pub fn last_index<A>(xs: &List<A>, x: A) -> BigInt
where
    A: Clone + Equal + 'static
{
    let i = (*index(rev(xs.clone())))(x);
    let n = size_list(xs);
    if i.clone() == n.clone() {
        i
    } else {
        ({
            let (m, n) = (n.clone(), (i + one_nat()).clone());
            if m <= n {
                BigInt::ZERO
            } else {
                m - n
            }
        })
    }
}

// borrow-optimized by shared parameters
pub fn map_index<B, A>
    (n: &BigInt, f: Rc<dyn Fn(BigInt, A) -> B>, x2: List<A>) -> List<B>
where
    A: Clone + 'static,
    B: Clone + 'static
{
    match (n, f, x2) {
        (_, _, List::Nil) => {
            List::Nil
        },
        (n, f, List::Cons(x, p0)) => {
            let xs = *p0;
            List::Cons((*f)(n.clone(), x.clone()), Box::new(map_index(&suc(n), f, xs.clone())))
        },
    }
}

// borrow-optimized by shared parameters
pub fn remove_nth<A>(i: &BigInt, x1: List<A>) -> List<A>
where
    A: Clone + 'static
{
    match (i, x1) {
        (_, List::Nil) => {
            List::Nil
        },
        (i, List::Cons(x, p0)) => {
            let xs = *p0;
            if i.clone() == BigInt::ZERO {
                xs.clone()
            } else {
                List::Cons(x.clone(), Box::new(remove_nth(&({
                    let (m, n) = (i.clone().clone(), one_nat().clone());
                    if m <= n {
                        BigInt::ZERO
                    } else {
                        m - n
                    }
                }), xs.clone())))
            }
        },
    }
}

