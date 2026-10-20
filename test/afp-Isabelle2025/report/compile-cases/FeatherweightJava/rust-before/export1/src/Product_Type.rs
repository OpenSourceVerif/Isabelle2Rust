use crate::Arith::Natural;
use crate::Arith::Zero;
use crate::Arith::one_natural;
use crate::Code_Evaluation::Term;
use crate::HOL::Equal;
use crate::List::List;
use crate::Option::Option;
use crate::Orderings::Ord;
use crate::Pure::Itself;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::Quickcheck_Random::collapse;
use crate::Random::select_weight;
use crate::String::Literal;
use crate::Typerep::Typerepa;

use std::rc::Rc;

#[derive(Clone)]
pub enum Unit {
    Unity
}

impl Equal for Unit {
    fn equal (x0: Unit, x1: Unit) -> bool {
        true
    }
}

pub fn apsnd <B, C, A> (f: Rc<dyn Fn(A) -> B>, x1: (C, A)) -> (C, B)
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static
{
    match (f, x1) {
        (f, (x, y)) =>
            (x.clone(), (*f)(y.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn scomp <D, A, C, B>
    (f: Rc<dyn Fn(A) -> (B, C)>, g: Rc<dyn Fn(B, C) -> D>) -> Rc<dyn Fn(A) -> D>
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static,
    D : Clone + 'static
{
    let g_cap = g.clone();
    let f_cap = f.clone();
    Rc::new(move |x: A| -> D {
        match (*f_cap)(x.clone()) {
            (a, b) =>
                (*g_cap)(a.clone(), b.clone()),
            _ =>
                panic!("non-exhaustive match")
        }
    })
}

pub fn fst <A, B> (x0: (A, B)) -> A
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        (x1, _) =>
            x1.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn snd <B, A> (x0: (A, B)) -> B
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        (_, x2) =>
            x2.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn random_aux_unit
    (x0: Natural, x1: Natural,
      s: (Natural, Natural)) -> ((Unit, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
    (*collapse(((Rc::new(move |a: (Natural, Natural)| -> (Rc<dyn Fn((Natural, Natural)) -> ((Unit, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>, (Natural, Natural)) {
        (*select_weight(List::Cons ((one_natural(), ((Rc::new(move |aa: (Natural, Natural)| -> ((Unit, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
            ((
                Unit::Unity,
                ((Rc::new(move |_: Unit| -> Term {
                    Term::Const (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil)))
                })) as Rc<dyn Fn(Unit) -> Term>)
            ), aa.clone())
        })) as Rc<dyn Fn((Natural, Natural)) -> ((Unit, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)), Box::new(List::Nil))))(a.clone())
    })) as Rc<dyn Fn((Natural, Natural)) -> (Rc<dyn Fn((Natural, Natural)) -> ((Unit, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>, (Natural, Natural))>)))(s.clone())
}

impl crate::Quickcheck_Random::Random for Unit {
    fn random
        (i: Natural,
          eta_arg_0: (Natural, Natural)) -> ((Unit, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
        random_aux_unit(i.clone(), i.clone(), eta_arg_0.clone())
    }
}

impl crate::Code_Evaluation::TermOf for Unit {
    fn term_of (x0: Unit) -> Term {
        let Unit::Unity = x0;
        Term::Const (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil)))
    }
}

impl crate::Typerep::Typerep for Unit {
    fn typerep (x0: Itself<Unit>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil))
    }
}

impl crate::Quickcheck_Exhaustive::FullExhaustive for Unit {
    fn full_exhaustive
        (f: Rc<dyn Fn((Unit, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>,
          i: Natural) -> Option<(bool, List<Term>)> {
        if <Natural as Ord>::less(<Natural as Zero>::zero(), i.clone()) {
            (*f)((
                Unit::Unity,
                ((Rc::new(move |_: Unit| -> Term {
                    Term::Const (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil)))
                })) as Rc<dyn Fn(Unit) -> Term>)
            ))
        } else {
            Option::None
        }
    }
}

impl crate::Quickcheck_Narrowing::PartialTermOf for Unit {
    fn partial_term_of (x0: Itself<Unit>, x1: NarrowingTerm) -> Term {
        match x1 {
            NarrowingTerm::NarrowingVariable (_, _) =>
                Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil))),
            NarrowingTerm::NarrowingConstructor (p0, p0a) =>
                panic!("non-exhaustive match"),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
