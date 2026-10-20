use crate::Finite_Set::Finite;
use crate::List::List;
use crate::List::list_all;
use crate::List::list_ex;
use crate::List::mapa;
use crate::List::product;
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

impl <A : Clone + Enum + 'static,  B : Clone + Enum + 'static> Enum for (A, B) {
    fn enum_all (p: Rc<dyn Fn((A, B)) -> bool>) -> bool {
        <A as Enum>::enum_all(
            (({
                let p_cap = p.clone();
                Rc::new(move |x: A| -> bool {
                    <B as Enum>::enum_all(
                        (({
                            let x_cap = x.clone();
                            let p_capa = p_cap.clone();
                            Rc::new(move |y: B| -> bool {
                                (*p_capa)((x_cap.clone(), y.clone()))
                            })
                        }) as Rc<dyn Fn(B) -> bool>)
                    )
                })
            }) as Rc<dyn Fn(A) -> bool>)
        )
    }
    fn enum_ex (p: Rc<dyn Fn((A, B)) -> bool>) -> bool {
        <A as Enum>::enum_ex(
            (({
                let p_cap = p.clone();
                Rc::new(move |x: A| -> bool {
                    <B as Enum>::enum_ex(
                        (({
                            let x_cap = x.clone();
                            let p_capa = p_cap.clone();
                            Rc::new(move |y: B| -> bool {
                                (*p_capa)((x_cap.clone(), y.clone()))
                            })
                        }) as Rc<dyn Fn(B) -> bool>)
                    )
                })
            }) as Rc<dyn Fn(A) -> bool>)
        )
    }
    fn enuma () -> List<(A, B)> {
        product(<A as Enum>::enuma(), <B as Enum>::enuma())
    }
}

pub fn enum_the<A>(x0: Rc<dyn Fn(A) -> bool>) -> A
where
    A : Clone + 'static
{
    panic!("Enum.enum_the")
}
