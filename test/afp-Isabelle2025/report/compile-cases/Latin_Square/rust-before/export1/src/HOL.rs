use crate::Enum::Enum;

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
