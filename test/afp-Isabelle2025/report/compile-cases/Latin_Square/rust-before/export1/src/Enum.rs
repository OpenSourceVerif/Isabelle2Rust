use crate::Finite_Set::Finite;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;

use std::rc::Rc;

pub trait Enum : Finite {
    fn enuma () -> List<Self> where Self: Sized;
    fn enum_all (x0: Rc<dyn Fn(Self) -> bool>) -> bool where Self: Sized;
    fn enum_ex (x0: Rc<dyn Fn(Self) -> bool>) -> bool where Self: Sized;
}

impl <A : Clone + Enum + 'static,  B : Clone + Equal + 'static> Equal for
    Rc<dyn Fn(A) -> B> {
    fn equal (f: Rc<dyn Fn(A) -> B>, g: Rc<dyn Fn(A) -> B>) -> bool {
        <A as Enum>::enum_all(
            (({
                let g_cap = g.clone();
                let f_cap = f.clone();
                Rc::new(move |x: A| -> bool {
                    eq((*f_cap)(x.clone()), (*g_cap)(x.clone()))
                })
            }) as Rc<dyn Fn(A) -> bool>)
        )
    }
}
