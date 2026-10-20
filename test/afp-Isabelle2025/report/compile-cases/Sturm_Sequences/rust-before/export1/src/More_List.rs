use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Fun::comp;
use crate::List::List;
use crate::List::drop_while;
use crate::List::nth;
use crate::List::rev;
use crate::List::size_list;

use std::rc::Rc;

pub fn nth_default <A> (dflt: A, xs: List<A>, n: BigInt) -> A
where
    A : Clone + 'static
{
    if n.clone() < size_list(xs.clone()) {
        nth(xs.clone(), n.clone())
    } else {
        dflt.clone()
    }
}

pub fn strip_while <A>
    (p: Rc<dyn Fn(A) -> bool>) -> Rc<dyn Fn(List<A>) -> List<A>>
where
    A : Clone + 'static
{
    (({
        let p_cap = p.clone();
        Rc::new(move |a: List<A>| -> List<A> {
            (*comp((({
                let p_capa = p_cap.clone();
                Rc::new(move |aa: List<A>| -> List<A> {
                    (*comp(((Rc::new(move |ab: List<A>| -> List<A> {
                        rev(ab.clone())
                    })) as Rc<dyn Fn(List<A>) -> List<A>>), (({
                        let p_capb = p_capa.clone();
                        Rc::new(move |ab: List<A>| -> List<A> {
                            drop_while(p_capb.clone(), ab.clone())
                        })
                    }) as Rc<dyn Fn(List<A>) -> List<A>>)))(aa.clone())
                })
            }) as Rc<dyn Fn(List<A>) -> List<A>>), ((Rc::new(move |aa: List<A>| -> List<A> {
                rev(aa.clone())
            })) as Rc<dyn Fn(List<A>) -> List<A>>)))(a.clone())
        })
    }) as Rc<dyn Fn(List<A>) -> List<A>>)
}
