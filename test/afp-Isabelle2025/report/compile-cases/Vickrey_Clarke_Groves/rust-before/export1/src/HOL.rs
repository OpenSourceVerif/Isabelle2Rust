use crate::Enum::Enum;
use crate::Enum::enum_the;
use crate::List::List;
use crate::List::filter;

use std::rc::Rc;

pub trait Equal {
    fn equal (x0: Self, x1: Self) -> bool where Self: Sized;
}

pub fn ex <A> (p: Rc<dyn Fn(A) -> bool>) -> bool
where
    A : Clone + Enum + 'static
{
    <A as Enum>::enum_ex(p.clone())
}

pub fn eq <A> (a: A, b: A) -> bool
where
    A : Clone + Equal + 'static
{
    <A as Equal>::equal(a.clone(), b.clone())
}

pub fn all <A> (p: Rc<dyn Fn(A) -> bool>) -> bool
where
    A : Clone + Enum + 'static
{
    <A as Enum>::enum_all(p.clone())
}

pub fn the <A> (p: Rc<dyn Fn(A) -> bool>) -> A
where
    A : Clone + Enum + 'static
{
    match filter(p.clone(), <A as Enum>::enuma()) {
        List::Nil =>
            enum_the(p.clone()),
        List::Cons (x, p0a) =>
            match *p0a {
                List::Nil =>
                    x.clone(),
                List::Cons (_, _) =>
                    enum_the(p.clone()),
                _ =>
                    panic!("non-exhaustive match")
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn implies (p: bool, pa: bool) -> bool {
    match (p, pa) {
        (_, true) =>
            true,
        (p, false) =>
            ! p.clone(),
        (true, p) =>
            p.clone(),
        (false, _) =>
            true,
        _ =>
            panic!("non-exhaustive match")
    }
}
