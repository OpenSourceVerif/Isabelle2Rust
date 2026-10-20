use crate::List::List;
use crate::List::fold;
use crate::Orderings::Linorder;
use crate::Set::Set;

use std::rc::Rc;

pub fn max <A> (x0: Set<A>) -> A
where
    A : Clone + Linorder + 'static
{
    match x0 {
        Set::Set (List::Cons (x, p0)) =>
            {
                let xs = *p0;
                fold(((Rc::new(move |a: A, b: A| -> A {
                    crate::Orderings::max(a.clone(), b.clone())
                })) as Rc<dyn Fn(A, A) -> A>), xs.clone(), x.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}
