use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::suc;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::Pure::Itself;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::Quickcheck_Narrowing::PartialTermOf;
use crate::String::Literal;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;

use std::marker::PhantomData;

use std::rc::Rc;

impl <A : Clone + PartialTermOf + 'static> Typerep for List<A> {
    fn typerep (x0: Itself<Self>) -> Typerepa { panic!("unimplemented instance method: typerep") }
}

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

pub fn distinct <A> (x0: List<A>) -> bool
where
    A : Clone + Equal + 'static
{
    match x0 {
        List::Nil =>
            true,
        List::Cons (x, p0) =>
            {
                let xs = *p0;
                ! member(xs.clone(), x.clone()) && distinct(xs.clone())
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

pub fn list_all2 <B, A>
    (p: Rc<dyn Fn(A, B) -> bool>, xs: List<A>, ys: List<B>) -> bool
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (p, xs, ys) {
        (p, List::Cons (x, p0), List::Cons (y, p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                (*p)(x.clone(), y.clone()) &&
                  list_all2(p.clone(), xs.clone(), ys.clone())
            },
        (_, xs, List::Nil) =>
            null(xs.clone()),
        (_, List::Nil, ys) =>
            null(ys.clone()),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_list <A> (x: Rc<dyn Fn(A) -> BigInt>, xa1: List<A>) -> BigInt
where
    A : Clone + 'static
{
    match (x, xa1) {
        (_, List::Nil) =>
            BigInt::ZERO,
        (x, List::Cons (x21, p0)) =>
            {
                let x22 = *p0;
                (*x)(x21.clone()) + size_list(x.clone(), x22.clone()) +
                  suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
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

impl <A : Clone + TermOf + 'static> TermOf for List<A> {
    fn term_of (x0: List<A>) -> Term {
        match x0 {
            List::Nil =>
                Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))),
            List::Cons (a, p0) =>
                {
                    let b = *p0;
                    Term::App (Box::new(Term::App (Box::new(Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))), Box::new(<A as TermOf>::term_of(a.clone())))), Box::new(<List<A> as TermOf>::term_of(b.clone())))
                },
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl <A : Clone + PartialTermOf + 'static> PartialTermOf for List<A> {
    fn partial_term_of (x0: Itself<List<A>>, x1: NarrowingTerm) -> Term {
        match x1 {
            NarrowingTerm::NarrowingVariable (_, _) =>
                Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))),
            NarrowingTerm::NarrowingConstructor (p0, p0a) =>
                panic!("non-exhaustive match"),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
