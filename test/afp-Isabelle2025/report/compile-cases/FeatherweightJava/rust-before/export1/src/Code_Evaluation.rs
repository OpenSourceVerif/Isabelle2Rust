use crate::Product_Type::Unit;
use crate::Pure::Itself;
use crate::String::Literal;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;

use std::rc::Rc;

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

pub fn valapp <B, A>
    (x0: (Rc<dyn Fn(A) -> B>, Rc<dyn Fn(Unit) -> Term>),
      x1: (A, Rc<dyn Fn(Unit) -> Term>)) -> (B, Rc<dyn Fn(Unit) -> Term>)
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (x0, x1) {
        ((f, tf), (x, tx)) =>
            (
                (*f)(x.clone()),
                (({
                    let tx_cap = tx.clone();
                    let tf_cap = tf.clone();
                    Rc::new(move |_: Unit| -> Term {
                        Term::App (Box::new((*tf_cap)(Unit::Unity)), Box::new((*tx_cap)(Unit::Unity)))
                    })
                }) as Rc<dyn Fn(Unit) -> Term>)
            ),
        _ =>
            panic!("non-exhaustive match")
    }
}
