use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::HOL::Equal;
use crate::List::List;
use crate::List::hd;
use crate::List::insort_key;
use crate::List::mapa;
use crate::List::member;
use crate::List::null;
use crate::List::tl;
use crate::Map::map_of;
use crate::Option::Option;
use crate::Orderings::Linorder;
use crate::Product_Type::fst;
use crate::Product_Type::snd;
use crate::Pure::Itself;
use crate::String::Literal;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;

use std::marker::PhantomData;

use std::rc::Rc;

#[derive(Clone)]
pub enum Pq<B, A> {
    AbsPq (List<(B, A)>)
}

pub fn alist_of <A, B> (x0: Pq<B, A>) -> List<(B, A)>
where
    B : Clone + 'static,
    A : Clone + Linorder + 'static
{
    let Pq::AbsPq (x) = x0;
    x.clone()
}

pub fn min <A, B> (q: Pq<A, B>) -> A
where
    A : Clone + 'static,
    B : Clone + Linorder + 'static
{
    fst(hd(alist_of(q.clone())))
}

pub fn is_empty <B, A> (q: Pq<A, B>) -> bool
where
    A : Clone + 'static,
    B : Clone + Linorder + 'static
{
    null(alist_of(q.clone()))
}

pub fn remove_min <B, A> (q: Pq<A, B>) -> Pq<A, B>
where
    A : Clone + 'static,
    B : Clone + Linorder + 'static
{
    Pq::AbsPq (
        if is_empty(q.clone()) {
            List::Nil
        } else {
            tl(alist_of(q.clone()))
        }
    )
}

pub fn pop <B, A> (q: Pq<A, B>) -> Option<(A, Pq<A, B>)>
where
    A : Clone + 'static,
    B : Clone + Linorder + 'static
{
    if is_empty(q.clone()) {
        Option::None
    } else {
        Option::Some ((min(q.clone()), remove_min(q.clone())))
    }
}

pub fn values <A, B> (q: Pq<A, B>) -> List<A>
where
    A : Clone + 'static,
    B : Clone + Linorder + 'static
{
    mapa(((Rc::new(move |a: (A, B)| -> A {
        fst(a.clone())
    })) as Rc<dyn Fn((A, B)) -> A>), alist_of(q.clone()))
}

pub fn push <B, A> (k: A, p: B, q: Pq<A, B>) -> Pq<A, B>
where
    A : Clone + Equal + 'static,
    B : Clone + Linorder + 'static
{
    Pq::AbsPq (
        if ! member(values(q.clone()), k.clone()) {
            insort_key(((Rc::new(move |a: (A, B)| -> B {
                snd(a.clone())
            })) as Rc<dyn Fn((A, B)) -> B>), (k.clone(), p.clone()), alist_of(q.clone()))
        } else {
            alist_of(q.clone())
        }
    )
}

pub fn empty <B, A> () -> Pq<A, B>
where
    A : Clone + 'static,
    B : Clone + Linorder + 'static
{
    Pq::AbsPq (List::Nil)
}

pub fn priority <B, A> (q: Pq<A, B>) -> Rc<dyn Fn(A) -> Option<B>>
where
    A : Clone + Equal + 'static,
    B : Clone + Linorder + 'static
{
    (({
        let q_cap = q.clone();
        Rc::new(move |a: A| -> Option<B> {
            map_of(alist_of(q_cap.clone()), a.clone())
        })
    }) as Rc<dyn Fn(A) -> Option<B>>)
}

pub fn priorities <B, A> (q: Pq<A, B>) -> List<B>
where
    A : Clone + 'static,
    B : Clone + Linorder + 'static
{
    mapa(((Rc::new(move |a: (A, B)| -> B {
        snd(a.clone())
    })) as Rc<dyn Fn((A, B)) -> B>), alist_of(q.clone()))
}

impl <A : Clone + Typerep + TermOf + 'static, 
       B : Clone + Typerep + TermOf + Linorder + 'static>
    TermOf for Pq<A, B> {
    fn term_of (x: Pq<A, B>) -> Term {
        Term::App (Box::new(Term::Const (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, false, false, false, false, true, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil)))))), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil)))))), Box::new(List::Nil)))))))), Box::new(<List<(A, B)> as TermOf>::term_of(alist_of(x.clone()))))
    }
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static> Typerep for
    Pq<A, B> {
    fn typerep (x0: Itself<Pq<A, B>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil))))))
    }
}
