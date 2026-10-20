use crate::Arith::MonoidAdd;
use crate::Arith::Plus;
use crate::Arith::Zero;
use crate::List::List;
use crate::List::foldr;

use std::rc::Rc;

pub fn sum_list <A> (xs: List<A>) -> A
where
    A : Clone + MonoidAdd + 'static
{
    (*foldr(((Rc::new(move |a: A, b: A| -> A {
        <A as Plus>::plus(a.clone(), b.clone())
    })) as Rc<dyn Fn(A, A) -> A>), xs.clone()))(<A as Zero>::zero())
}
