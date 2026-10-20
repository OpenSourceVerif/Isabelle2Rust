use crate::Product_Type::Unit;
use crate::Set::Set;

use std::rc::Rc;

#[derive(Clone)]
pub enum Filter<A> {
    Principal (Set<A>),
    AbstractFilter (Box<Rc<dyn Fn(Unit) -> Filter<A>>>)
}
