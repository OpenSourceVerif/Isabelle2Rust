use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Argmax::argmax;
use crate::Argmax::filterpositions2;
use crate::Arith::CommMonoidAdd;
use crate::Arith::Minus;
use crate::Arith::One;
use crate::Arith::Zero;
use crate::Fun::comp;
use crate::Groups_Big::sum;
use crate::HOL::Equal;
use crate::Lattices_Big::max;
use crate::List::List;
use crate::List::mapa;
use crate::List::maps;
use crate::List::nth;
use crate::MiscTools::finestpart;
use crate::MiscTools::to_function;
use crate::Orderings::Linorder;
use crate::Partitions::all_partitions_list;
use crate::Product_Type::fst;
use crate::Product_Type::product;
use crate::Product_Type::snd;
use crate::Relation::converse;
use crate::RelationOperators::outside;
use crate::RelationOperators::paste;
use crate::RelationProperties::injections_alg;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::image;
use crate::Set::insert;
use crate::Set::member;
use crate::Set::pow;
use crate::Set::remove;
use crate::Set::sup_set;
use crate::Set::the_elem;
use crate::UniformTieBreaking::pseudo_allocation;
use crate::UniformTieBreaking::random_el;
use crate::UniformTieBreaking::to_function_with_fallback_alg;

use std::rc::Rc;

pub fn chosen_allocation_alg <B, A, C>
    (n: Set<A>, omega: List<B>, b: Rc<dyn Fn((A, Set<B>)) -> C>,
      r: BigInt) -> Set<(A, Set<B>)>
where
    A : Clone + Equal + Linorder + 'static,
    B : Clone + Equal + 'static,
    C : Clone + CommMonoidAdd + Equal + Linorder + 'static
{
    random_el(mapa((({
        let omega_cap = omega.clone();
        let n_cap = n.clone();
        Rc::new(move |a: BigInt| -> Set<(A, Set<B>)> {
            nth(mapa(((Rc::new(move |aa: Set<(Set<B>, A)>| -> Set<(A, Set<B>)> {
                converse(aa.clone())
            })) as Rc<dyn Fn(Set<(Set<B>, A)>) -> Set<(A, Set<B>)>>), maps(
                (({
                    let n_capa = n_cap.clone();
                    Rc::new(move |l: List<Set<B>>| -> List<Set<(Set<B>, A)>> {
                        injections_alg(l.clone(), n_capa.clone())
                    })
                }) as Rc<dyn Fn(List<Set<B>>) -> List<Set<(Set<B>, A)>>>),
                all_partitions_list(omega_cap.clone())
            )), a.clone())
        })
    }) as Rc<dyn Fn(BigInt) -> Set<(A, Set<B>)>>), filterpositions2(
        (({
            let omega_cap = omega.clone();
            let n_cap = n.clone();
            let b_cap = b.clone();
            Rc::new(move |x: Set<(A, Set<B>)>| -> bool {
                member(x.clone(), (*(*comp(((Rc::new(move |boundary_arg: Rc<dyn Fn(Set<(A, Set<B>)>) -> C>| {
                    (({
                        let boundary_arg_cap = boundary_arg.clone();
                        Rc::new(move |a: Set<Set<(A, Set<B>)>>| -> Set<Set<(A, Set<B>)>> {
                            argmax(boundary_arg_cap.clone(), a.clone())
                        })
                    }) as Rc<dyn Fn(Set<Set<(A, Set<B>)>>) -> Set<Set<(A, Set<B>)>>>)
                })) as Rc<dyn Fn(Rc<dyn Fn(Set<(A, Set<B>)>) -> C>) -> Set<Set<(A, Set<B>)>>>), ((Rc::new(move |boundary_arg: Rc<dyn Fn((A, Set<B>)) -> C>| {
                    (({
                        let boundary_arg_cap = boundary_arg.clone();
                        Rc::new(move |boundary_arh: Set<(A, Set<B>)>| -> C {
                            sum(boundary_arg_cap.clone(), boundary_arh.clone())
                        })
                    }) as Rc<dyn Fn(Set<(A, Set<B>)>) -> C>)
                })) as Rc<dyn Fn(Rc<dyn Fn((A, Set<B>)) -> C>) -> Rc<dyn Fn(Set<(A, Set<B>)>) -> C>>)))(b_cap.clone()))(Set::Set (mapa(((Rc::new(move |a: Set<(Set<B>, A)>| -> Set<(A, Set<B>)> {
                    converse(a.clone())
                })) as Rc<dyn Fn(Set<(Set<B>, A)>) -> Set<(A, Set<B>)>>), maps(
                    (({
                        let n_capa = n_cap.clone();
                        Rc::new(move |l: List<Set<B>>| -> List<Set<(Set<B>, A)>> {
                            injections_alg(l.clone(), n_capa.clone())
                        })
                    }) as Rc<dyn Fn(List<Set<B>>) -> List<Set<(Set<B>, A)>>>),
                    all_partitions_list(omega_cap.clone())
                )))))
            })
        }) as Rc<dyn Fn(Set<(A, Set<B>)>) -> bool>),
        mapa(((Rc::new(move |a: Set<(Set<B>, A)>| -> Set<(A, Set<B>)> {
            converse(a.clone())
        })) as Rc<dyn Fn(Set<(Set<B>, A)>) -> Set<(A, Set<B>)>>), maps(
            (({
                let n_cap = n.clone();
                Rc::new(move |l: List<Set<B>>| -> List<Set<(Set<B>, A)>> {
                    injections_alg(l.clone(), n_cap.clone())
                })
            }) as Rc<dyn Fn(List<Set<B>>) -> List<Set<(Set<B>, A)>>>),
            all_partitions_list(omega.clone())
        ))
    )), r.clone())
}

pub fn summed_bid_vector_alg <C, B, A>
    (bids: Rc<dyn Fn((A, Set<B>)) -> C>, n: Set<A>,
      omega: Set<B>) -> Rc<dyn Fn((A, Set<B>)) -> C>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static,
    C : Clone + CommMonoidAdd + 'static
{
    (({
        let omega_cap = omega.clone();
        let n_cap = n.clone();
        let bids_cap = bids.clone();
        Rc::new(move |a: (A, Set<B>)| -> C {
            (*to_function_with_fallback_alg(image(
                (({
                    let bids_capa = bids_cap.clone();
                    Rc::new(move |pair: (A, Set<B>)| -> ((A, Set<B>), C) {
                        (pair.clone(), sum(
                            (({
                                let pair_cap = pair.clone();
                                let bids_capb = bids_capa.clone();
                                Rc::new(move |g: Set<B>| -> C {
                                    (*bids_capb)((fst(pair_cap.clone()), g.clone()))
                                })
                            }) as Rc<dyn Fn(Set<B>) -> C>),
                            finestpart(snd(pair.clone()))
                        ))
                    })
                }) as Rc<dyn Fn((A, Set<B>)) -> ((A, Set<B>), C)>),
                product(n_cap.clone(), remove(bot_set::<B>(), pow(omega_cap.clone())))
            ), <C as Zero>::zero()))(a.clone())
        })
    }) as Rc<dyn Fn((A, Set<B>)) -> C>)
}

pub fn maxbid_alg <B, A>
    (a: Set<(A, Set<B>)>, n: Set<A>,
      omega: Set<B>) -> Rc<dyn Fn((A, Set<B>)) -> BigInt>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    (({
        let a_cap = a.clone();
        let omega_cap = omega.clone();
        let n_cap = n.clone();
        Rc::new(move |b: (A, Set<B>)| -> BigInt {
            (*to_function_with_fallback_alg(paste(product(product(n_cap.clone(), finestpart(omega_cap.clone())), insert(BigInt::ZERO, bot_set::<BigInt>())), product(pseudo_allocation(a_cap.clone()), insert(<BigInt as One>::one(), bot_set::<BigInt>()))), BigInt::ZERO))(b.clone())
        })
    }) as Rc<dyn Fn((A, Set<B>)) -> BigInt>)
}

pub fn tiebids_alg <B, A>
    (a: Set<(A, Set<B>)>, n: Set<A>,
      omega: Set<B>) -> Rc<dyn Fn((A, Set<B>)) -> BigInt>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    (({
        let omega_cap = omega.clone();
        let n_cap = n.clone();
        let a_cap = a.clone();
        Rc::new(move |b: (A, Set<B>)| -> BigInt {
            (*summed_bid_vector_alg((({
                let omega_capa = omega_cap.clone();
                let n_capa = n_cap.clone();
                let a_capa = a_cap.clone();
                Rc::new(move |ba: (A, Set<B>)| -> BigInt {
                    (*maxbid_alg(a_capa.clone(), n_capa.clone(), omega_capa.clone()))(ba.clone())
                })
            }) as Rc<dyn Fn((A, Set<B>)) -> BigInt>), n_cap.clone(), omega_cap.clone()))(b.clone())
        })
    }) as Rc<dyn Fn((A, Set<B>)) -> BigInt>)
}

pub fn resolving_bid_alg <B, A, C>
    (n: Set<A>, omega: List<B>, bids: Rc<dyn Fn((A, Set<B>)) -> C>,
      random: BigInt) -> Rc<dyn Fn((A, Set<B>)) -> BigInt>
where
    A : Clone + Equal + Linorder + 'static,
    B : Clone + Equal + 'static,
    C : Clone + CommMonoidAdd + Equal + Linorder + 'static
{
    (({
        let random_cap = random.clone();
        let bids_cap = bids.clone();
        let omega_cap = omega.clone();
        let n_cap = n.clone();
        Rc::new(move |a: (A, Set<B>)| -> BigInt {
            (*tiebids_alg(chosen_allocation_alg(n_cap.clone(), omega_cap.clone(), bids_cap.clone(), random_cap.clone()), n_cap.clone(), Set::Set (omega_cap.clone())))(a.clone())
        })
    }) as Rc<dyn Fn((A, Set<B>)) -> BigInt>)
}

pub fn random_bids_alg <A, B>
    (n: Set<BigInt>, omega: List<A>, b: Rc<dyn Fn((BigInt, Set<A>)) -> B>,
      random: BigInt) -> Rc<dyn Fn((BigInt, Set<A>)) -> BigInt>
where
    A : Clone + Equal + 'static,
    B : Clone + CommMonoidAdd + Equal + Linorder + 'static
{
    (({
        let random_cap = random.clone();
        let b_cap = b.clone();
        let omega_cap = omega.clone();
        let n_cap = n.clone();
        Rc::new(move |a: (BigInt, Set<A>)| -> BigInt {
            (*resolving_bid_alg(sup_set(n_cap.clone(), insert(BigInt::ZERO, bot_set::<BigInt>())), omega_cap.clone(), b_cap.clone(), random_cap.clone()))(a.clone())
        })
    }) as Rc<dyn Fn((BigInt, Set<A>)) -> BigInt>)
}

pub fn vcga_alg_without_losers <A, B>
    (n: Set<BigInt>, omega: List<A>, b: Rc<dyn Fn((BigInt, Set<A>)) -> B>,
      r: BigInt) -> Set<(BigInt, Set<A>)>
where
    A : Clone + Equal + 'static,
    B : Clone + CommMonoidAdd + Equal + Linorder + 'static
{
    outside(the_elem(argmax((({
        let r_cap = r.clone();
        let b_cap = b.clone();
        let omega_cap = omega.clone();
        let n_cap = n.clone();
        Rc::new(move |a: Set<(BigInt, Set<A>)>| -> BigInt {
            sum((({
                let r_capa = r_cap.clone();
                let b_capa = b_cap.clone();
                let omega_capa = omega_cap.clone();
                let n_capa = n_cap.clone();
                Rc::new(move |aa: (BigInt, Set<A>)| -> BigInt {
                    (*random_bids_alg(n_capa.clone(), omega_capa.clone(), b_capa.clone(), r_capa.clone()))(aa.clone())
                })
            }) as Rc<dyn Fn((BigInt, Set<A>)) -> BigInt>), a.clone())
        })
    }) as Rc<dyn Fn(Set<(BigInt, Set<A>)>) -> BigInt>), argmax((({
        let b_cap = b.clone();
        Rc::new(move |a: Set<(BigInt, Set<A>)>| -> B {
            sum(b_cap.clone(), a.clone())
        })
    }) as Rc<dyn Fn(Set<(BigInt, Set<A>)>) -> B>), Set::Set (mapa(((Rc::new(move |a: Set<(Set<A>, BigInt)>| -> Set<(BigInt, Set<A>)> {
        converse(a.clone())
    })) as Rc<dyn Fn(Set<(Set<A>, BigInt)>) -> Set<(BigInt, Set<A>)>>), maps(
        (({
            let n_cap = n.clone();
            Rc::new(move |l: List<Set<A>>| -> List<Set<(Set<A>, BigInt)>> {
                injections_alg(l.clone(), sup_set(insert(BigInt::ZERO, bot_set::<BigInt>()), n_cap.clone()))
            })
        }) as Rc<dyn Fn(List<Set<A>>) -> List<Set<(Set<A>, BigInt)>>>),
        all_partitions_list(omega.clone())
    )))))), insert(BigInt::ZERO, bot_set::<BigInt>()))
}

pub fn vcga_alg <A, B>
    (n: Set<BigInt>, omega: List<A>, b: Rc<dyn Fn((BigInt, Set<A>)) -> B>,
      r: BigInt) -> Set<(BigInt, Set<A>)>
where
    A : Clone + Equal + 'static,
    B : Clone + CommMonoidAdd + Equal + Linorder + 'static
{
    paste(product(n.clone(), insert(bot_set::<A>(), bot_set::<Set<A>>())), vcga_alg_without_losers(n.clone(), omega.clone(), b.clone(), r.clone()))
}

pub fn vcgp_alg <A, B>
    (na: Set<BigInt>, omega: List<BigInt>,
      b: Rc<dyn Fn((BigInt, Set<BigInt>)) -> A>, x3: B, n: BigInt,
      winningAllocation: Set<(BigInt, Set<BigInt>)>) -> A
where
    A : Clone + CommMonoidAdd + Minus + Linorder + 'static,
    B : Clone + 'static
{
    <A as Minus>::minus(max(image((({
        let b_cap = b.clone();
        Rc::new(move |a: Set<(BigInt, Set<BigInt>)>| -> A {
            sum(b_cap.clone(), a.clone())
        })
    }) as Rc<dyn Fn(Set<(BigInt, Set<BigInt>)>) -> A>), image(
        ((Rc::new(move |f: Set<(BigInt, Set<BigInt>)>| -> Set<(BigInt, Set<BigInt>)> {
            outside(f.clone(), insert(BigInt::ZERO, bot_set::<BigInt>()))
        })) as Rc<dyn Fn(Set<(BigInt, Set<BigInt>)>) -> Set<(BigInt, Set<BigInt>)>>),
        Set::Set (mapa(((Rc::new(move |a: Set<(Set<BigInt>, BigInt)>| -> Set<(BigInt, Set<BigInt>)> {
            converse(a.clone())
        })) as Rc<dyn Fn(Set<(Set<BigInt>, BigInt)>) -> Set<(BigInt, Set<BigInt>)>>), maps(
            (({
                let na_cap = na.clone();
                let n_cap = n.clone();
                Rc::new(move |l: List<Set<BigInt>>| -> List<Set<(Set<BigInt>, BigInt)>> {
                    injections_alg(l.clone(), sup_set(remove(n_cap.clone(), na_cap.clone()), insert(BigInt::ZERO, bot_set::<BigInt>())))
                })
            }) as Rc<dyn Fn(List<Set<BigInt>>) -> List<Set<(Set<BigInt>, BigInt)>>>),
            all_partitions_list(omega.clone())
        )))
    ))), sum(b.clone(), outside(winningAllocation.clone(), insert(n.clone(), bot_set::<BigInt>()))))
}

pub fn tiebids <B, A>
    () -> Rc<dyn Fn(Set<(A, Set<B>)>, Set<A>, Set<B>, (A, Set<B>)) -> BigInt>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    Rc::new(move |allocation: Set<(A, Set<B>)>, n: Set<A>, g: Set<B>, eta_arg: (A, Set<B>)| -> BigInt {
        (*to_function(image(
            (({
                let allocation_cap = allocation.clone();
                let g_cap = g.clone();
                let n_cap = n.clone();
                Rc::new(move |pair: (A, Set<B>)| -> ((A, Set<B>), BigInt) {
                    (pair.clone(), sum(
                        (({
                            let pair_cap = pair.clone();
                            let allocation_capa = allocation_cap.clone();
                            let g_capa = g_cap.clone();
                            let n_capa = n_cap.clone();
                            Rc::new(move |ga: Set<B>| -> BigInt {
                                (*to_function(paste(product(product(n_capa.clone(), finestpart(g_capa.clone())), insert(BigInt::ZERO, bot_set::<BigInt>())), product(pseudo_allocation(allocation_capa.clone()), insert(<BigInt as One>::one(), bot_set::<BigInt>())))))((fst(pair_cap.clone()), ga.clone()))
                            })
                        }) as Rc<dyn Fn(Set<B>) -> BigInt>),
                        finestpart(snd(pair.clone()))
                    ))
                })
            }) as Rc<dyn Fn((A, Set<B>)) -> ((A, Set<B>), BigInt)>),
            product(n.clone(), remove(bot_set::<B>(), pow(g.clone())))
        )))(eta_arg.clone())
    })
}
