use crate::HOL::Equal;
use crate::List::List;
use crate::List::map_filter;
use crate::List::maps;
use crate::Option::Option;
use crate::Relation::rangea;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::insert;
use crate::Set::member;
use crate::Set::sup_set;

use std::rc::Rc;

pub fn injections_alg <B, A> (x0: List<A>, y: List<B>) -> List<Set<(A, B)>>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    match (x0, y) {
        (List::Nil, _) =>
            List::Cons (bot_set::<(A, B)>(), Box::new(List::Nil)),
        (List::Cons (x, p0), y) =>
            {
                let xs = *p0;
                maps(
                    (({
                        let y_cap = y.clone();
                        let x_cap = x.clone();
                        Rc::new(move |r: Set<(A, B)>| -> List<Set<(A, B)>> {
                            map_filter(
                                (({
                                    let x_capa = x_cap.clone();
                                    let r_cap = r.clone();
                                    Rc::new(move |xa: B| -> Option<Set<(A, B)>> {
                                        if ! member(xa.clone(), rangea(r_cap.clone())) {
    Option::Some (sup_set(r_cap.clone(), insert((x_capa.clone(), xa.clone()), bot_set::<(A, B)>())))
} else {
    Option::None
}
                                    })
                                }) as Rc<dyn Fn(B) -> Option<Set<(A, B)>>>),
                                y_cap.clone()
                            )
                        })
                    }) as Rc<dyn Fn(Set<(A, B)>) -> List<Set<(A, B)>>>),
                    injections_alg(xs.clone(), y.clone())
                )
            },
        _ =>
            panic!("non-exhaustive match")
    }
}
