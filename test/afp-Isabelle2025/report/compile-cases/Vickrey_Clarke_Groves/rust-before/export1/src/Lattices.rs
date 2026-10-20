use crate::Arith::Minus;

use std::rc::Rc;

impl <A : Clone + 'static,  B : Clone + Minus + 'static> Minus for
    Rc<dyn Fn(A) -> B> {
    fn minus
        (a: Rc<dyn Fn(A) -> B>, b: Rc<dyn Fn(A) -> B>) -> Rc<dyn Fn(A) -> B> {
        let b_cap = b.clone();
        let a_cap = a.clone();
        Rc::new(move |x: A| -> B {
            <B as Minus>::minus((*a_cap)(x.clone()), (*b_cap)(x.clone()))
        })
    }
}
