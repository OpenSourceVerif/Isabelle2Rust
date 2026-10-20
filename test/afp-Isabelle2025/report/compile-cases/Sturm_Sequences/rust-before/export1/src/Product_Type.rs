use crate::HOL::Equal;
use crate::HOL::eq;

use std::rc::Rc;

#[derive(Clone)]
pub enum Unit {
    Unity
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

impl <A : Clone + Equal + 'static,  B : Clone + Equal + 'static> Equal for
    (A, B) {
    fn equal (x0: (A, B), x1: (A, B)) -> bool {
        match (x0, x1) {
            ((x1, x2), (y1, y2)) =>
                eq(x1.clone(), y1.clone()) && eq(x2.clone(), y2.clone()),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
