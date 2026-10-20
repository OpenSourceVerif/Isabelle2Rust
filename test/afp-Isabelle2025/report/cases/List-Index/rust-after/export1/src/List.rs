use num_bigint::*;

use num_traits::sign::Signed as _;

use crate::Arith::suc;

use std::rc::Rc;

#[derive(Clone)]
pub enum List <A> {
    Nil,
    Cons(A, Box<List<A>>),
}

pub fn fold<B, A>(f: Rc<dyn Fn(A, B) -> B>, x1: List<A>, s: B) -> B
where
    A: Clone + 'static,
    B: Clone + 'static
{
    match (f, x1, s) {
        (f, List::Cons(x, p0), s) => {
            let xs = *p0;
            fold(f.clone(), xs, (*f)(x, s))
        },
        (_, List::Nil, s) => {
            s
        },
    }
}

pub fn rev<A>(xs: List<A>) -> List<A>
where
    A: Clone + 'static
{
    fold((Rc::new(move |a: A, b: List<A>| -> List<A> {
        List::Cons(a, Box::new(b))
    })) as Rc<dyn Fn(A, List<A>) -> List<A>>, xs, List::Nil)
}

// borrow-optimized by shared parameters
pub fn gen_length<A>(n: BigInt, x1: &List<A>) -> BigInt
where
    A: Clone + 'static
{
    match (n, x1) {
        (n, List::Cons(_, p0)) => {
            let xs = p0.as_ref();
            gen_length(suc(&n), xs)
        },
        (n, List::Nil) => {
            n
        },
    }
}

// borrow-optimized by shared parameters
pub fn size_list<A>(x: &List<A>) -> BigInt
where
    A: Clone + 'static
{
    gen_length(BigInt::ZERO, x)
}

