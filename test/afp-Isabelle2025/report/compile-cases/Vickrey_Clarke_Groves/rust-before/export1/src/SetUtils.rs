use crate::HOL::Equal;
use crate::Orderings::Ord;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::insert;
use crate::Set::the_elem;

pub fn trivial <A> (x: Set<A>) -> bool
where
    A : Clone + Equal + 'static
{
    <Set<A> as Ord>::less_eq(x.clone(), insert(the_elem(x.clone()), bot_set::<A>()))
}
