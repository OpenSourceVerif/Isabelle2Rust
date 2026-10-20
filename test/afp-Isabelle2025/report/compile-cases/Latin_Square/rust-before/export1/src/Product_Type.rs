use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::mapa;
use crate::List::maps;
use crate::Set::Set;

use std::rc::Rc;

impl <A : Clone + Equal + 'static,  B : Clone + Equal + 'static> Equal for
    (A, B) {
    fn equal (x0: (A, B), x1: (A, B)) -> bool {
        match (x0, x1) {
            ((x1, x2), (y1, y2)) =>
                eq(x1.clone(), y1.clone()) && eq(x2.clone(), y2.clone()),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

#[derive(Clone)]
pub enum Unit {
    Unity
}

pub fn apsnd <B, C, A> (f: Rc<dyn Fn(A) -> B>, x1: (C, A)) -> (C, B)
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static
{
    match (f, x1) {
        (f, (x, y)) =>
            (x.clone(), (*f)(y.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn scomp <D, A, C, B>
    (f: Rc<dyn Fn(A) -> (B, C)>, g: Rc<dyn Fn(B, C) -> D>) -> Rc<dyn Fn(A) -> D>
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static,
    D : Clone + 'static
{
    let g_cap = g.clone();
    let f_cap = f.clone();
    Rc::new(move |x: A| -> D {
        match (*f_cap)(x.clone()) {
            (a, b) =>
                (*g_cap)(a.clone(), b.clone()),
            _ =>
                panic!("non-exhaustive match")
        }
    })
}

pub fn product <B, A> (x0: Set<A>, x1: Set<B>) -> Set<(A, B)>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (x0, x1) {
        (Set::Set (xs), Set::Set (ys)) =>
            Set::Set (maps(
                (({
                    let ys_cap = ys.clone();
                    Rc::new(move |x: A| -> List<(A, B)> {
                        mapa((({
                            let x_cap = x.clone();
                            Rc::new(move |a: B| -> (A, B) {
                                (x_cap.clone(), a.clone())
                            })
                        }) as Rc<dyn Fn(B) -> (A, B)>), ys_cap.clone())
                    })
                }) as Rc<dyn Fn(A) -> List<(A, B)>>),
                xs.clone()
            )),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn fst <A, B> (x0: (A, B)) -> A
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        (x1, _) =>
            x1.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn snd <B, A> (x0: (A, B)) -> B
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        (_, x2) =>
            x2.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}
