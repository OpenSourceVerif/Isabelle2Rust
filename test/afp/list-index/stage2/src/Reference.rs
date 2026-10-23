use num_bigint::*;

use num_traits::sign::Signed as _;

use std::rc::Rc;

pub trait Equal { fn equal(x0 : Self, x1 : Self) -> bool where Self : Sized ; }
#[derive(Clone)]
pub enum Num {
    One,
    Bit0(Box<Num>),
    Bit1(Box<Num>),
}

#[derive(Clone)]
pub enum List <A> {
    Nil,
    Cons(A, Box<List<A>>),
}

pub fn eq<A>(a: A, b: A) -> bool
where
    A: Clone + Equal + 'static
{
    <A as Equal>::equal(a, b)
}

pub fn one_nat() -> BigInt {
    BigInt::from_bytes_be(Sign::Plus, &[1])
}

// borrow-optimized by shared parameters
pub fn suc(n: &BigInt) -> BigInt {
    n.clone() + one_nat()
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
pub fn size_list<A>(x: &List<A>) -> BigInt
where
    A: Clone + 'static
{
    gen_length(BigInt::ZERO, x)
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

