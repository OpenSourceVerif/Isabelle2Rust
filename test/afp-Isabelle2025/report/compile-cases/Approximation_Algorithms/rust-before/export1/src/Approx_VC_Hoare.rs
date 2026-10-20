use crate::HOL::Equal;
use crate::Set::Set;
use crate::Set::ball;
use crate::Set::inf_set;
use crate::Set::is_empty;

use std::rc::Rc;

pub fn vertex_cover <A> (e: Set<Set<A>>, c: Set<A>) -> bool
where
    A : Clone + Equal + 'static
{
    ball(
        e.clone(),
        (({
            let c_cap = c.clone();
            Rc::new(move |ea: Set<A>| -> bool {
                ! is_empty(inf_set(ea.clone(), c_cap.clone()))
            })
        }) as Rc<dyn Fn(Set<A>) -> bool>)
    )
}
