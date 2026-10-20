use crate::Arith::Plus;
use crate::Arith::Times;
use crate::Arith::Zero;
use crate::List::List;
use crate::List::foldr;
use crate::Rings::CommSemiring0;

use std::rc::Rc;

pub fn horner_sum <B, A> (f: Rc<dyn Fn(A) -> B>, a: B, xs: List<A>) -> B
where
    A : Clone + 'static,
    B : Clone + CommSemiring0 + 'static
{
    (*foldr(
        (({
            let a_cap = a.clone();
            let f_cap = f.clone();
            Rc::new(move |x: A, b: B| -> B {
                <B as Plus>::plus((*f_cap)(x.clone()), <B as Times>::times(a_cap.clone(), b.clone()))
            })
        }) as Rc<dyn Fn(A, B) -> B>),
        xs.clone()
    ))(<B as Zero>::zero())
}
