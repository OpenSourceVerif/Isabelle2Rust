use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Argmax::argmax_list;
use crate::Arith::Minus;
use crate::Complete_Lattices::sup_set;
use crate::Enum::Enum;
use crate::Groups_Big::sum;
use crate::HOL::Equal;
use crate::Lattices_Big::max;
use crate::List::List;
use crate::List::mapa;
use crate::List::maps;
use crate::Partitions::all_partitions;
use crate::Partitions::all_partitions_alg;
use crate::Partitions::all_partitions_list;
use crate::Real::Real;
use crate::Relation::converse;
use crate::RelationOperators::outside;
use crate::RelationProperties::injections;
use crate::RelationProperties::injections_alg;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::image;
use crate::Set::insert;
use crate::Set::remove;

use std::rc::Rc;

pub fn winning_allocation_alg <A>
    (n: Set<BigInt>, g: List<BigInt>,
      t: Rc<dyn Fn(List<Set<(BigInt, Set<BigInt>)>>) -> A>,
      b: Rc<dyn Fn((BigInt, Set<BigInt>)) -> Real>) -> A
where
    A : Clone + 'static
{
    (*t)(argmax_list((({
        let b_cap = b.clone();
        Rc::new(move |a: Set<(BigInt, Set<BigInt>)>| -> Real {
            sum(b_cap.clone(), a.clone())
        })
    }) as Rc<dyn Fn(Set<(BigInt, Set<BigInt>)>) -> Real>), mapa(((Rc::new(move |a: Set<(Set<BigInt>, BigInt)>| -> Set<(BigInt, Set<BigInt>)> {
        converse(a.clone())
    })) as Rc<dyn Fn(Set<(Set<BigInt>, BigInt)>) -> Set<(BigInt, Set<BigInt>)>>), maps(
        (({
            let n_cap = n.clone();
            Rc::new(move |l: List<Set<BigInt>>| -> List<Set<(Set<BigInt>, BigInt)>> {
                injections_alg(l.clone(), n_cap.clone())
            })
        }) as Rc<dyn Fn(List<Set<BigInt>>) -> List<Set<(Set<BigInt>, BigInt)>>>),
        all_partitions_list(g.clone())
    ))))
}

pub fn payments_alg
    (n: Set<BigInt>, g: List<BigInt>,
      t: Rc<dyn Fn(List<Set<(BigInt, Set<BigInt>)>>) -> Set<(BigInt, Set<BigInt>)>>) -> Rc<dyn Fn(Rc<dyn Fn((BigInt, Set<BigInt>)) -> Real>,
                   BigInt) -> Real> {
    (({
        let t_cap = t.clone();
        let g_cap = g.clone();
        let n_cap = n.clone();
        Rc::new(move |boundary_arg: Rc<dyn Fn((BigInt, Set<BigInt>)) -> Real>, boundary_arh: BigInt| {
            (*(*<Rc<dyn Fn(Rc<dyn Fn((BigInt, Set<BigInt>)) -> Real>) -> Rc<dyn Fn(BigInt) -> Real>> as Minus>::minus(
                (({
                    let g_capa = g_cap.clone();
                    let n_capa = n_cap.clone();
                    Rc::new(move |boundary_ari: Rc<dyn Fn((BigInt, Set<BigInt>)) -> Real>| {
                        (({
                            let boundary_ari_cap = boundary_ari.clone();
                            let g_capb = g_capa.clone();
                            let n_capb = n_capa.clone();
                            Rc::new(move |boundary_arj: BigInt| -> Real {
                                (*{
                                    let g_capc = g_capb.clone();
                                    let n_capc = n_capb.clone();
                                    Rc::new(move |b: Rc<dyn Fn((BigInt, Set<BigInt>)) -> Real>, na: BigInt| {
                                        max(image((({
    let b_cap = b.clone();
    Rc::new(move |a: Set<(BigInt, Set<BigInt>)>| -> Real {
        sum(b_cap.clone(), a.clone())
    })
}) as Rc<dyn Fn(Set<(BigInt, Set<BigInt>)>) -> Real>), Set::Set (mapa(((Rc::new(move |a: Set<(Set<BigInt>, BigInt)>| -> Set<(BigInt, Set<BigInt>)> {
    converse(a.clone())
})) as Rc<dyn Fn(Set<(Set<BigInt>, BigInt)>) -> Set<(BigInt, Set<BigInt>)>>), maps(
    (({
        let n_capd = n_capc.clone();
        let na_cap = na.clone();
        Rc::new(move |l: List<Set<BigInt>>| -> List<Set<(Set<BigInt>, BigInt)>> {
            injections_alg(l.clone(), remove(na_cap.clone(), n_capd.clone()))
        })
    }) as Rc<dyn Fn(List<Set<BigInt>>) -> List<Set<(Set<BigInt>, BigInt)>>>),
    all_partitions_list(g_capc.clone())
)))))
                                    })
                                })(boundary_ari_cap.clone(), boundary_arj.clone())
                            })
                        }) as Rc<dyn Fn(BigInt) -> Real>)
                    })
                }) as Rc<dyn Fn(Rc<dyn Fn((BigInt, Set<BigInt>)) -> Real>) -> Rc<dyn Fn(BigInt) -> Real>>),
                (({
                    let t_capa = t_cap.clone();
                    let g_capa = g_cap.clone();
                    let n_capa = n_cap.clone();
                    Rc::new(move |boundary_ari: Rc<dyn Fn((BigInt, Set<BigInt>)) -> Real>| {
                        (({
                            let boundary_ari_cap = boundary_ari.clone();
                            let t_capb = t_capa.clone();
                            let g_capb = g_capa.clone();
                            let n_capb = n_capa.clone();
                            Rc::new(move |boundary_arj: BigInt| -> Real {
                                (*{
                                    let t_capc = t_capb.clone();
                                    let g_capc = g_capb.clone();
                                    let n_capc = n_capb.clone();
                                    Rc::new(move |b: Rc<dyn Fn((BigInt, Set<BigInt>)) -> Real>, na: BigInt| {
                                        sum(b.clone(), outside(winning_allocation_alg(n_capc.clone(), g_capc.clone(), t_capc.clone(), b.clone()), insert(na.clone(), bot_set::<BigInt>())))
                                    })
                                })(boundary_ari_cap.clone(), boundary_arj.clone())
                            })
                        }) as Rc<dyn Fn(BigInt) -> Real>)
                    })
                }) as Rc<dyn Fn(Rc<dyn Fn((BigInt, Set<BigInt>)) -> Real>) -> Rc<dyn Fn(BigInt) -> Real>>)
            ))(boundary_arg.clone()))(boundary_arh.clone())
        })
    }) as Rc<dyn Fn(Rc<dyn Fn((BigInt, Set<BigInt>)) -> Real>, BigInt) -> Real>)
}

pub fn possible_allocations_alg
    (g: Set<BigInt>, n: Set<BigInt>) -> List<Set<(Set<BigInt>, BigInt)>> {
    maps(
        (({
            let n_cap = n.clone();
            Rc::new(move |y: List<Set<BigInt>>| -> List<Set<(Set<BigInt>, BigInt)>> {
                injections_alg(y.clone(), n_cap.clone())
            })
        }) as Rc<dyn Fn(List<Set<BigInt>>) -> List<Set<(Set<BigInt>, BigInt)>>>),
        all_partitions_alg(g.clone())
    )
}

pub fn possible_allocations_rel <B, A>
    (g: Set<A>, n: Set<B>) -> Set<Set<(Set<A>, B)>>
where
    A : Clone + Enum + Equal + 'static,
    B : Clone + Enum + Equal + 'static
{
    sup_set(image(
        (({
            let n_cap = n.clone();
            Rc::new(move |y: Set<Set<A>>| -> Set<Set<(Set<A>, B)>> {
                injections(y.clone(), n_cap.clone())
            })
        }) as Rc<dyn Fn(Set<Set<A>>) -> Set<Set<(Set<A>, B)>>>),
        all_partitions(g.clone())
    ))
}
