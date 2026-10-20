use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::suc;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::Pure::Itself;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::Quickcheck_Narrowing::PartialTermOf;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::insert;
use crate::String::Literal;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;

use std::marker::PhantomData;

use std::rc::Rc;

impl <A : Clone + PartialTermOf + 'static> Typerep for Option<A> {
    fn typerep (x0: Itself<Self>) -> Typerepa { panic!("unimplemented instance method: typerep") }
}

#[derive(Clone)]
pub enum Option<A> {
    None,
    Some (A)
}

pub fn is_none <A> (x0: Option<A>) -> bool
where
    A : Clone + 'static
{
    match x0 {
        Option::Some (_) =>
            false,
        Option::None =>
            true,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn map_option <B, A> (f: Rc<dyn Fn(A) -> B>, x1: Option<A>) -> Option<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (_, Option::None) =>
            Option::None,
        (f, Option::Some (x2)) =>
            Option::Some ((*f)(x2.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rel_option <B, A>
    (r: Rc<dyn Fn(A, B) -> bool>, x1: Option<A>, x2: Option<B>) -> bool
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (r, x1, x2) {
        (_, Option::None, Option::Some (_)) =>
            false,
        (_, Option::Some (_), Option::None) =>
            false,
        (_, Option::None, Option::None) =>
            true,
        (r, Option::Some (x2), Option::Some (y2)) =>
            (*r)(x2.clone(), y2.clone()),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn set_option <A> (x0: Option<A>) -> Set<A>
where
    A : Clone + Equal + 'static
{
    match x0 {
        Option::None =>
            bot_set::<A>(),
        Option::Some (x2) =>
            insert(x2.clone(), bot_set::<A>()),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_option <A> (x: Rc<dyn Fn(A) -> BigInt>, xa1: Option<A>) -> BigInt
where
    A : Clone + 'static
{
    match (x, xa1) {
        (_, Option::None) =>
            suc(BigInt::ZERO),
        (x, Option::Some (x2)) =>
            (*x)(x2.clone()) + suc(BigInt::ZERO),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_optiona <A> (x0: Option<A>) -> BigInt
where
    A : Clone + 'static
{
    match x0 {
        Option::None =>
            suc(BigInt::ZERO),
        Option::Some (_) =>
            suc(BigInt::ZERO),
        _ =>
            panic!("non-exhaustive match")
    }
}

impl <A : Clone + Equal + 'static> Equal for Option<A> {
    fn equal (x0: Option<A>, x1: Option<A>) -> bool {
        match (x0, x1) {
            (Option::None, Option::Some (_)) =>
                false,
            (Option::Some (_), Option::None) =>
                false,
            (Option::Some (x2), Option::Some (y2)) =>
                eq(x2.clone(), y2.clone()),
            (Option::None, Option::None) =>
                true,
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl <A : Clone + TermOf + 'static> TermOf for Option<A> {
    fn term_of (x0: Option<A>) -> Term {
        match x0 {
            Option::None =>
                Term::Const (Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))),
            Option::Some (a) =>
                Term::App (Box::new(Term::Const (Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))))), Box::new(<A as TermOf>::term_of(a.clone()))),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl <A : Clone + PartialTermOf + 'static> PartialTermOf for Option<A> {
    fn partial_term_of (x0: Itself<Option<A>>, x1: NarrowingTerm) -> Term {
        match x1 {
            NarrowingTerm::NarrowingVariable (_, _) =>
                Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerepa::Typerep (Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))),
            NarrowingTerm::NarrowingConstructor (p0, p0a) =>
                panic!("non-exhaustive match"),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
