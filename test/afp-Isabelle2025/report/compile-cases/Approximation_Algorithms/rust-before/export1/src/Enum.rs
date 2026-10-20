use crate::Finite_Set::Finite;
use crate::List::List;

use std::rc::Rc;

pub trait Enum : Finite {
    fn enuma () -> List<Self> where Self: Sized;
    fn enum_all (x0: Rc<dyn Fn(Self) -> bool>) -> bool where Self: Sized;
    fn enum_ex (x0: Rc<dyn Fn(Self) -> bool>) -> bool where Self: Sized;
}
