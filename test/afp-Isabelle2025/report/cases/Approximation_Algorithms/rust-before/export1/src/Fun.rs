use std::rc::Rc;

pub fn id <A> (x: A) -> A
where
    A : Clone + 'static
{
    (*Rc::new(move |xa: A| {
        xa.clone()
    }))(x.clone())
}

pub fn comp <B, C, A>
    (f: Rc<dyn Fn(A) -> B>, g: Rc<dyn Fn(C) -> A>) -> Rc<dyn Fn(C) -> B>
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static
{
    let g_cap = g.clone();
    let f_cap = f.clone();
    Rc::new(move |x: C| -> B {
        (*f_cap)((*g_cap)(x.clone()))
    })
}
