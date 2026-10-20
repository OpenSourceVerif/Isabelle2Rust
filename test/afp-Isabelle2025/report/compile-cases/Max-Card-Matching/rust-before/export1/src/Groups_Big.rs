use crate::Arith::CommMonoidAdd;
use crate::Groups_List::sum_list;
use crate::HOL::Equal;
use crate::List::List;
use crate::List::mapa;
use crate::List::remdups;
use crate::Set::Set;

use std::rc::Rc;

pub fn sum <B, A> (g: Rc<dyn Fn(A) -> B>, x1: Set<A>) -> B
where
    A : Clone + Equal + 'static,
    B : Clone + CommMonoidAdd + 'static
{
    match (g, x1) {
        (g, Set::Set (xs)) =>
            sum_list(mapa(g.clone(), remdups(xs.clone()))),
        _ =>
            panic!("non-exhaustive match")
    }
}
