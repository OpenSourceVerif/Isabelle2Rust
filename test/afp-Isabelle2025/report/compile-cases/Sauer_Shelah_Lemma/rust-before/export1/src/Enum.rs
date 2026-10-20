use crate::Finite_Set::Finite;
use crate::List::List;
use crate::List::list_all;
use crate::List::list_ex;
use crate::List::mapa;
use crate::List::subseqs;
use crate::Set::Set;

use std::rc::Rc;

pub trait Enum : Finite {
    fn enuma () -> List<Self> where Self: Sized;
    fn enum_all (x0: Rc<dyn Fn(Self) -> bool>) -> bool where Self: Sized;
    fn enum_ex (x0: Rc<dyn Fn(Self) -> bool>) -> bool where Self: Sized;
}

impl <A : Clone + Enum + 'static> Enum for Set<A> {
    fn enum_all (p: Rc<dyn Fn(Set<A>) -> bool>) -> bool {
        list_all(p.clone(), <Set<A> as Enum>::enuma())
    }
    fn enum_ex (p: Rc<dyn Fn(Set<A>) -> bool>) -> bool {
        list_ex(p.clone(), <Set<A> as Enum>::enuma())
    }
    fn enuma () -> List<Set<A>> {
        mapa(((Rc::new(move |a: List<A>| -> Set<A> {
            Set::Set (a.clone())
        })) as Rc<dyn Fn(List<A>) -> Set<A>>), subseqs(<A as Enum>::enuma()))
    }
}
