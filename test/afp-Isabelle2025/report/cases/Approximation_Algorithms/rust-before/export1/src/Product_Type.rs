use std::rc::Rc;

#[derive(Clone)]
pub enum Unit {
    Unity
}

pub fn map_prod <D, B, C, A>
    (f: Rc<dyn Fn(A) -> B>, g: Rc<dyn Fn(C) -> D>, x2: (A, C)) -> (B, D)
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static,
    D : Clone + 'static
{
    match (f, g, x2) {
        (f, g, (a, b)) =>
            ((*f)(a.clone()), (*g)(b.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}
