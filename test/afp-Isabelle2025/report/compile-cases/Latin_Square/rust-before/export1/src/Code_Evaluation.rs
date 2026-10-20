use crate::String::Literal;
use crate::Typerep::Typerep;

#[derive(Clone)]
pub enum Term {
    Const (Literal, Typerep),
    App (Box<Term>, Box<Term>),
    Abs (Literal, Typerep, Box<Term>),
    Free (Literal, Typerep)
}
