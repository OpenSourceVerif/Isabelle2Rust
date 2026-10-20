use crate::HOL::Equal;
use crate::List::List;
use crate::List::fold;
use crate::Set::Set;
use crate::Set::bot_set;

use std::rc::Rc;

pub fn sup_set <A> (x0: Set<Set<A>>) -> Set<A>
where
    A : Clone + Equal + 'static
{
    match x0 {
        Set::Set (xs) =>
            fold(((Rc::new(move |a: Set<A>, b: Set<A>| -> Set<A> {
                crate::Set::sup_set(a.clone(), b.clone())
            })) as Rc<dyn Fn(Set<A>,
                              Set<A>) -> Set<A>>), xs.clone(), bot_set::<A>()),
        _ =>
            panic!("non-exhaustive match")
    }
}
