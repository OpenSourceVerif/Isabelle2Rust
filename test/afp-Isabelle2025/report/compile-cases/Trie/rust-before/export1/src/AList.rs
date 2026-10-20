use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::Product_Type::fst;
use crate::Product_Type::snd;

use std::rc::Rc;

pub fn update <B, A> (k: A, v: B, x2: List<(A, B)>) -> List<(A, B)>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match (k, v, x2) {
        (k, v, List::Nil) =>
            List::Cons ((k.clone(), v.clone()), Box::new(List::Nil)),
        (k, v, List::Cons (p, p0)) =>
            {
                let ps = *p0;
                if eq(fst(p.clone()), k.clone()) {
                    List::Cons ((k.clone(), v.clone()), Box::new(ps.clone()))
                } else {
                    List::Cons (p.clone(), Box::new(update(k.clone(), v.clone(), ps.clone())))
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn delete_aux <B, A> (ka: A, x1: List<(A, B)>) -> List<(A, B)>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match (ka, x1) {
        (_, List::Nil) =>
            List::Nil,
        (ka, List::Cons ((k, v), p0)) =>
            {
                let xs = *p0;
                if eq(ka.clone(), k.clone()) {
                    xs.clone()
                } else {
                    List::Cons ((k.clone(), v.clone()), Box::new(delete_aux(ka.clone(), xs.clone())))
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn update_with_aux <A, B>
    (v: A, k: B, f: Rc<dyn Fn(A) -> A>, x3: List<(B, A)>) -> List<(B, A)>
where
    A : Clone + 'static,
    B : Clone + Equal + 'static
{
    match (v, k, f, x3) {
        (v, k, f, List::Nil) =>
            List::Cons ((k.clone(), (*f)(v.clone())), Box::new(List::Nil)),
        (v, k, f, List::Cons (p, p0)) =>
            {
                let ps = *p0;
                if eq(fst(p.clone()), k.clone()) {
                    List::Cons ((k.clone(), (*f)(snd(p.clone()))), Box::new(ps.clone()))
                } else {
                    List::Cons (p.clone(), Box::new(update_with_aux(v.clone(), k.clone(), f.clone(), ps.clone())))
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}
