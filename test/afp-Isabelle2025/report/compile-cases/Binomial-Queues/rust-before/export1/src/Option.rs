use std::rc::Rc;

#[derive(Clone)]
pub enum Option<A> {
    None,
    Some (A)
}

pub fn map_option <B, A> (f: Rc<dyn Fn(A) -> B>, x1: Option<A>) -> Option<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (_, Option::None) =>
            Option::None,
        (f, Option::Some (x2)) =>
            Option::Some ((*f)(x2.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}
