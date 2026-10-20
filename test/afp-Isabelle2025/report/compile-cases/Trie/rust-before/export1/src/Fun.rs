use std::rc::Rc;

pub fn id <A> (x: A) -> A
where
    A : Clone + 'static
{
    (*Rc::new(move |xa: A| {
        xa.clone()
    }))(x.clone())
}
