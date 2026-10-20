use crate::Fun::id;
use crate::Product_Type::scomp;

use std::rc::Rc;

pub fn collapse <A, B>
    (f: Rc<dyn Fn(A) -> (Rc<dyn Fn(A) -> (B, A)>, A)>) -> Rc<dyn Fn(A) -> (B, A)>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    (({
        let f_cap = f.clone();
        Rc::new(move |a: A| -> (B, A) {
            (*scomp(f_cap.clone(), ((Rc::new(move |aa: Rc<dyn Fn(A) -> (B, A)>, b: A| -> (B, A) {
                (*id(aa.clone()))(b.clone())
            })) as Rc<dyn Fn(Rc<dyn Fn(A) -> (B, A)>,
                              A) -> (B, A)>)))(a.clone())
        })
    }) as Rc<dyn Fn(A) -> (B, A)>)
}
