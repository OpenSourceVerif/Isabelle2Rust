use crate::HOL::Equal;
use crate::HOL::eq;

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

pub fn fun_upd <B, A> (f: Rc<dyn Fn(A) -> B>, a: A, b: B) -> Rc<dyn Fn(A) -> B>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    let f_cap = f.clone();
    let b_cap = b.clone();
    let a_cap = a.clone();
    Rc::new(move |x: A| -> B {
        if eq(x.clone(), a_cap.clone()) {
            b_cap.clone()
        } else {
            (*f_cap)(x.clone())
        }
    })
}
