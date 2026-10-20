use crate::List::List;
use crate::String::Literal;

#[derive(Clone)]
pub enum Typerep {
    Typerep (Literal, Box<List<Typerep>>)
}
