use crate::Arith::Num;
use crate::Code_Evaluation::Term;
use crate::List::List;
use crate::Pure::Itself;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::String::Literal;
use crate::Typerep::Typerepa;

pub trait Equal {
    fn equal (x0: Self, x1: Self) -> bool where Self: Sized;
}

pub fn eq <A> (a: A, b: A) -> bool
where
    A : Clone + Equal + 'static
{
    <A as Equal>::equal(a.clone(), b.clone())
}

impl crate::Code_Evaluation::TermOf for bool {
    fn term_of (x0: bool) -> Term {
        match x0 {
            true =>
                Term::Const (Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))), Typerepa::Typerep (Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))), Box::new(List::Nil))),
            false =>
                Term::Const (Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))), Box::new(List::Nil))),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl crate::Quickcheck_Narrowing::PartialTermOf for bool {
    fn partial_term_of (x0: Itself<bool>, x1: NarrowingTerm) -> Term {
        match x1 {
            NarrowingTerm::NarrowingVariable (_, _) =>
                Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerepa::Typerep (Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))), Box::new(List::Nil))),
            NarrowingTerm::NarrowingConstructor (p0, p0a) =>
                panic!("non-exhaustive match"),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl crate::Typerep::Typerep for bool {
    fn typerep (x0: Itself<Self>) -> Typerepa { panic!("unimplemented instance method: typerep") }
}
