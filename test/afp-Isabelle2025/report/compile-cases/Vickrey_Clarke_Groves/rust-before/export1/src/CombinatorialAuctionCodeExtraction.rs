use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::CombinatorialAuction::vcgp_alg;
use crate::Complete_Lattices::sup_set;
use crate::Fun::comp;
use crate::HOL::Equal;
use crate::List::List;
use crate::List::mapa;
use crate::List::sorted_list_of_set;
use crate::Orderings::Linorder;
use crate::Product_Type::fst;
use crate::Product_Type::snd;
use crate::Relation::domain;
use crate::RelationOperators::eval_rel;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::image;
use crate::Set::insert;
use crate::UniformTieBreaking::to_function_with_fallback_alg;

use std::rc::Rc;

pub fn participants_set <A, B> (b: List<(A, B)>) -> Set<A>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    image(((Rc::new(move |a: (A, B)| -> A {
        fst(a.clone())
    })) as Rc<dyn Fn((A, B)) -> A>), Set::Set (b.clone()))
}

pub fn bid2func_bid <B, A>
    (b: List<(A, (List<B>, BigInt))>) -> Rc<dyn Fn((A, Set<B>)) -> BigInt>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    (({
        let b_cap = b.clone();
        Rc::new(move |a: (A, Set<B>)| -> BigInt {
            (*to_function_with_fallback_alg(Set::Set (mapa(
                ((Rc::new(move |x: (A, (List<B>, BigInt))| -> ((A, Set<B>), BigInt) {
                    ((fst(x.clone()), Set::Set ((*comp(((Rc::new(move |aa: (List<B>, BigInt)| -> List<B> {
                        fst(aa.clone())
                    })) as Rc<dyn Fn((List<B>, BigInt)) -> List<B>>), ((Rc::new(move |aa: (A, (List<B>, BigInt))| -> (List<B>, BigInt) {
                        snd(aa.clone())
                    })) as Rc<dyn Fn((A, (List<B>, BigInt))) -> (List<B>, BigInt)>)))(x.clone()))), (*comp(((Rc::new(move |aa: (List<B>, BigInt)| -> BigInt {
                        snd(aa.clone())
                    })) as Rc<dyn Fn((List<B>, BigInt)) -> BigInt>), ((Rc::new(move |aa: (A, (List<B>, BigInt))| -> (List<B>, BigInt) {
                        snd(aa.clone())
                    })) as Rc<dyn Fn((A, (List<B>, BigInt))) -> (List<B>, BigInt)>)))(x.clone()))
                })) as Rc<dyn Fn((A, (List<B>, BigInt))) -> ((A, Set<B>), BigInt)>),
                b_cap.clone()
            )), BigInt::ZERO))(a.clone())
        })
    }) as Rc<dyn Fn((A, Set<B>)) -> BigInt>)
}

pub fn goods_list <B, C, A> (b: List<(A, (List<B>, C))>) -> List<B>
where
    A : Clone + 'static,
    B : Clone + Equal + Linorder + 'static,
    C : Clone + 'static
{
    sorted_list_of_set(sup_set(image(((Rc::new(move |a: (A, (List<B>, C))| -> Set<B> {
        (*comp(((Rc::new(move |aa: (List<B>, C)| -> Set<B> {
            (*comp(((Rc::new(move |ab: List<B>| -> Set<B> {
                Set::Set (ab.clone())
            })) as Rc<dyn Fn(List<B>) -> Set<B>>), ((Rc::new(move |ab: (List<B>, C)| -> List<B> {
                fst(ab.clone())
            })) as Rc<dyn Fn((List<B>, C)) -> List<B>>)))(aa.clone())
        })) as Rc<dyn Fn((List<B>, C)) -> Set<B>>), ((Rc::new(move |aa: (A, (List<B>, C))| -> (List<B>, C) {
            snd(aa.clone())
        })) as Rc<dyn Fn((A, (List<B>, C))) -> (List<B>, C)>)))(a.clone())
    })) as Rc<dyn Fn((A, (List<B>, C))) -> Set<B>>), Set::Set (b.clone()))))
}

pub fn payments <A>
    (b: List<(BigInt, (List<BigInt>, BigInt))>, r: A, n: BigInt,
      a: Set<(BigInt, Set<BigInt>)>) -> BigInt
where
    A : Clone + 'static
{
    vcgp_alg(participants_set(b.clone()), goods_list(b.clone()), (({
        let b_cap = b.clone();
        Rc::new(move |aa: (BigInt, Set<BigInt>)| -> BigInt {
            (*bid2func_bid(b_cap.clone()))(aa.clone())
        })
    }) as Rc<dyn Fn((BigInt, Set<BigInt>)) -> BigInt>), r.clone(), n.clone(), a.clone())
}

pub fn allocation_pretty_print <B, A>
    (a: Set<(A, Set<B>)>) -> Set<List<(A, List<B>)>>
where
    A : Clone + Equal + Linorder + 'static,
    B : Clone + Equal + Linorder + 'static
{
    insert(mapa(
        (({
            let a_cap = a.clone();
            Rc::new(move |x: A| -> (A, List<B>) {
                (x.clone(), sorted_list_of_set(eval_rel(a_cap.clone(), x.clone())))
            })
        }) as Rc<dyn Fn(A) -> (A, List<B>)>),
        (*comp(((Rc::new(move |aa: Set<A>| -> List<A> {
            sorted_list_of_set(aa.clone())
        })) as Rc<dyn Fn(Set<A>) -> List<A>>), ((Rc::new(move |aa: Set<(A, Set<B>)>| -> Set<A> {
            domain(aa.clone())
        })) as Rc<dyn Fn(Set<(A, Set<B>)>) -> Set<A>>)))(a.clone())
    ), bot_set::<List<(A, List<B>)>>())
}
