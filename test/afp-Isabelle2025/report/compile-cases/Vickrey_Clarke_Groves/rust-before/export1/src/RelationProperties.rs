use crate::Arith::Minus;
use crate::Enum::Enum;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::mapa;
use crate::List::maps;
use crate::List::sorted_list_of_set;
use crate::Orderings::Linorder;
use crate::Relation::converse;
use crate::Relation::domain;
use crate::Relation::rangea;
use crate::RelationOperators::paste;
use crate::RelationOperators::runiq;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::collect;
use crate::Set::image;
use crate::Set::inf_set;
use crate::Set::insert;
use crate::Set::pow;
use crate::Set::vimage;

use std::rc::Rc;

pub fn injections <B, A> (x: Set<A>, y: Set<B>) -> Set<Set<(A, B)>>
where
    A : Clone + Enum + Equal + 'static,
    B : Clone + Enum + Equal + 'static
{
    image(
        ((Rc::new(move |r: Set<(A, B)>| -> Set<(A, B)> {
            r.clone()
        })) as Rc<dyn Fn(Set<(A, B)>) -> Set<(A, B)>>),
        inf_set(image(
            ((Rc::new(move |r: Set<(A, B)>| -> Set<(A, B)> {
                r.clone()
            })) as Rc<dyn Fn(Set<(A, B)>) -> Set<(A, B)>>),
            collect(
                (({
                    let x_cap = x.clone();
                    Rc::new(move |r: Set<(A, B)>| -> bool {
                        eq(domain(r.clone()), x_cap.clone())
                    })
                }) as Rc<dyn Fn(Set<(A, B)>) -> bool>)
            )
        ), inf_set(image(
            ((Rc::new(move |r: Set<(A, B)>| -> Set<(A, B)> {
                r.clone()
            })) as Rc<dyn Fn(Set<(A, B)>) -> Set<(A, B)>>),
            image(
                ((Rc::new(move |r: Set<(A, B)>| -> Set<(A, B)> {
                    r.clone()
                })) as Rc<dyn Fn(Set<(A, B)>) -> Set<(A, B)>>),
                vimage(((Rc::new(move |a: Set<(A, B)>| -> Set<B> {
                    rangea(a.clone())
                })) as Rc<dyn Fn(Set<(A, B)>) -> Set<B>>), pow(y.clone()))
            )
        ), inf_set(image(
            ((Rc::new(move |r: Set<(A, B)>| -> Set<(A, B)> {
                r.clone()
            })) as Rc<dyn Fn(Set<(A, B)>) -> Set<(A, B)>>),
            image(
                ((Rc::new(move |r: Set<(A, B)>| -> Set<(A, B)> {
                    r.clone()
                })) as Rc<dyn Fn(Set<(A, B)>) -> Set<(A, B)>>),
                image(
                    ((Rc::new(move |r: Set<(A, B)>| -> Set<(A, B)> {
                        r.clone()
                    })) as Rc<dyn Fn(Set<(A, B)>) -> Set<(A, B)>>),
                    collect(((Rc::new(move |a: Set<(A, B)>| -> bool {
                        runiq(a.clone())
                    })) as Rc<dyn Fn(Set<(A, B)>) -> bool>))
                )
            )
        ), image(
            ((Rc::new(move |r: Set<(A, B)>| -> Set<(A, B)> {
                r.clone()
            })) as Rc<dyn Fn(Set<(A, B)>) -> Set<(A, B)>>),
            image(
                ((Rc::new(move |r: Set<(A, B)>| -> Set<(A, B)> {
                    r.clone()
                })) as Rc<dyn Fn(Set<(A, B)>) -> Set<(A, B)>>),
                image(
                    ((Rc::new(move |r: Set<(A, B)>| -> Set<(A, B)> {
                        r.clone()
                    })) as Rc<dyn Fn(Set<(A, B)>) -> Set<(A, B)>>),
                    collect(
                        ((Rc::new(move |r: Set<(A, B)>| -> bool {
                            runiq(converse(r.clone()))
                        })) as Rc<dyn Fn(Set<(A, B)>) -> bool>)
                    )
                )
            )
        ))))
    )
}

pub fn injections_alg <B, A> (x0: List<A>, y: Set<B>) -> List<Set<(A, B)>>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + Linorder + 'static
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
                            mapa(
                                (({
                                    let x_capa = x_cap.clone();
                                    let r_cap = r.clone();
                                    Rc::new(move |ya: B| -> Set<(A, B)> {
                                        paste(r_cap.clone(), insert((x_capa.clone(), ya.clone()), bot_set::<(A, B)>()))
                                    })
                                }) as Rc<dyn Fn(B) -> Set<(A, B)>>),
                                sorted_list_of_set(<Set<B> as Minus>::minus(y_cap.clone(), rangea(r.clone())))
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
