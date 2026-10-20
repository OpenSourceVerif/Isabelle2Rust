use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::rev;
use crate::List::zip;
use crate::Option::Option;

use std::rc::Rc;

pub fn map_of <B, A> (x0: List<(A, B)>, k: A) -> Option<B>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match (x0, k) {
        (List::Cons ((l, v), p0), k) =>
            {
                let ps = *p0;
                if eq(l.clone(), k.clone()) {
                    Option::Some (v.clone())
                } else {
                    map_of(ps.clone(), k.clone())
                }
            },
        (List::Nil, _) =>
            Option::None,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn map_add <B, A>
    (m1: Rc<dyn Fn(A) -> Option<B>>,
      m2: Rc<dyn Fn(A) -> Option<B>>) -> Rc<dyn Fn(A) -> Option<B>>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let m1_cap = m1.clone();
    let m2_cap = m2.clone();
    Rc::new(move |x: A| -> Option<B> {
        match (*m2_cap)(x.clone()) {
            Option::None =>
                (*m1_cap)(x.clone()),
            Option::Some (a) =>
                Option::Some (a.clone()),
            _ =>
                panic!("non-exhaustive match")
        }
    })
}

pub fn map_upds <B, A>
    (m: Rc<dyn Fn(A) -> Option<B>>, xs: List<A>,
      ys: List<B>) -> Rc<dyn Fn(A) -> Option<B>>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    (({
        let ys_cap = ys.clone();
        let xs_cap = xs.clone();
        let m_cap = m.clone();
        Rc::new(move |a: A| -> Option<B> {
            (*map_add(m_cap.clone(), (({
                let ys_capa = ys_cap.clone();
                let xs_capa = xs_cap.clone();
                Rc::new(move |aa: A| -> Option<B> {
                    map_of(rev(zip(xs_capa.clone(), ys_capa.clone())), aa.clone())
                })
            }) as Rc<dyn Fn(A) -> Option<B>>)))(a.clone())
        })
    }) as Rc<dyn Fn(A) -> Option<B>>)
}
