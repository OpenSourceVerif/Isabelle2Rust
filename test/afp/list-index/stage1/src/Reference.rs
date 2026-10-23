use num_bigint::*;
use num_traits::sign::Signed as _;

use std::rc::Rc;

pub trait Equal {
    fn equal (x0: Self, x1: Self) -> bool where Self: Sized;
}

#[derive(Clone)]
pub enum Num {
    One,
    Bit0 (Box<Num>),
    Bit1 (Box<Num>)
}

#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons (A, Box<List<A>>)
}

pub fn eq <A> (a: A, b: A) -> bool
where
    A : Clone + Equal + 'static
{
    <A as Equal>::equal(a.clone(), b.clone())
}

pub fn one_nat () -> BigInt {
    BigInt::from_bytes_be(Sign::Plus, &[1])
}

pub fn suc (n: BigInt) -> BigInt {
    n.clone() + one_nat()
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

pub fn find_index <A> (p: Rc<dyn Fn(A) -> bool>, x1: List<A>) -> BigInt
where
    A : Clone + 'static
{
    match (p, x1) {
        (_, List::Nil) =>
            BigInt::ZERO,
        (p, List::Cons (x, p0)) =>
            {
                let xs = *p0;
                if (*p)(x.clone()) {
                    BigInt::ZERO
                } else {
                    find_index(p.clone(), xs.clone()) + one_nat()
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn index <A> (xs: List<A>) -> Rc<dyn Fn(A) -> BigInt>
where
    A : Clone + Equal + 'static
{
    let xs_cap = xs.clone();
    Rc::new(move |a: A| -> BigInt {
        find_index(
            (({
                let a_cap = a.clone();
                Rc::new(move |x: A| -> bool {
                    eq(x.clone(), a_cap.clone())
                })
            }) as Rc<dyn Fn(A) -> bool>),
            xs_cap.clone()
        )
    })
}

pub fn size_list <A> (x: List<A>) -> BigInt
where
    A : Clone + 'static
{
    gen_length(BigInt::ZERO, x.clone())
}

pub fn last_index <A> (xs: List<A>, x: A) -> BigInt
where
    A : Clone + Equal + 'static
{
    let i = (*index(rev(xs.clone())))(x.clone());
    let n = size_list(xs.clone());
    if i.clone() == n.clone() {
        i.clone()
    } else {
        (match (n.clone().clone(), (i.clone() +
                                     one_nat()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
    }
}
