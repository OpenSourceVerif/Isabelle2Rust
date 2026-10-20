use crate::HOL::Equal;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::insert;
use crate::Set::is_empty;

pub fn wrap <A> (b: Set<A>) -> Set<Set<A>>
where
    A : Clone + Equal + 'static
{
    if is_empty(b.clone()) {
        bot_set::<Set<A>>()
    } else {
        insert(b.clone(), bot_set::<Set<A>>())
    }
}
