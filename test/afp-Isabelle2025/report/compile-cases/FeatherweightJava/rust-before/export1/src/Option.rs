use crate::HOL::Equal;
use crate::HOL::eq;

#[derive(Clone)]
pub enum Option<A> {
    None,
    Some (A)
}

impl <A : Clone + Equal + 'static> Equal for Option<A> {
    fn equal (x0: Option<A>, x1: Option<A>) -> bool {
        match (x0, x1) {
            (Option::None, Option::Some (_)) =>
                false,
            (Option::Some (_), Option::None) =>
                false,
            (Option::Some (x2), Option::Some (y2)) =>
                eq(x2.clone(), y2.clone()),
            (Option::None, Option::None) =>
                true,
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
