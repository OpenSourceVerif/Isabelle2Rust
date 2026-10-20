use crate::String::Literal;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;

#[derive(Clone)]
pub enum Term {
    Const (Literal, Typerepa),
    App (Box<Term>, Box<Term>),
    Abs (Literal, Typerepa, Box<Term>),
    Free (Literal, Typerepa)
}

pub trait TermOf : Typerep {
    fn term_of (x0: Self) -> Term where Self: Sized;
}
