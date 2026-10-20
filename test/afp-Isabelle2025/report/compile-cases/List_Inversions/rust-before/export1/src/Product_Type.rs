use crate::Complete_Lattices::sup_set;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::mapa;
use crate::List::maps;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::image;
use crate::Set::insert;

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

pub fn sigma <B, A> (a: Set<A>, b: Rc<dyn Fn(A) -> Set<B>>) -> Set<(A, B)>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    sup_set(image(
        (({
            let b_cap = b.clone();
            Rc::new(move |x: A| -> Set<(A, B)> {
                sup_set(image(
                    (({
                        let x_cap = x.clone();
                        Rc::new(move |y: B| -> Set<(A, B)> {
                            insert((x_cap.clone(), y.clone()), bot_set::<(A, B)>())
                        })
                    }) as Rc<dyn Fn(B) -> Set<(A, B)>>),
                    (*b_cap)(x.clone())
                ))
            })
        }) as Rc<dyn Fn(A) -> Set<(A, B)>>),
        a.clone()
    ))
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
