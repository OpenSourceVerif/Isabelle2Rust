use crate::List::List;
use crate::Pure::Itself;
use crate::String::Literal;

#[derive(Clone)]
pub enum Typerepa {
    Typerep (Literal, Box<List<Typerepa>>)
}

pub trait Typerep {
    fn typerep (x0: Itself<Self>) -> Typerepa where Self: Sized;
}
