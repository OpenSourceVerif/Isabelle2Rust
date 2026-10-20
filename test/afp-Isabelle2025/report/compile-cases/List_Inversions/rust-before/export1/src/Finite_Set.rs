use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::HOL::Equal;
use crate::List::List;
use crate::List::remdups;
use crate::List::size_list;
use crate::Set::Set;

pub fn card <A> (x0: Set<A>) -> BigInt
where
    A : Clone + Equal + 'static
{
    match x0 {
        Set::Set (xs) =>
            size_list(remdups(xs.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}
