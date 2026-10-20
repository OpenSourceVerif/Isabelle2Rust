use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Complete_Lattices::sup_set;
use crate::Euclidean_Rings::modulo_nat;
use crate::HOL::Equal;
use crate::List::List;
use crate::List::nth;
use crate::List::size_list;
use crate::MiscTools::finestpart;
use crate::Product_Type::fst;
use crate::Product_Type::product;
use crate::Product_Type::snd;
use crate::Relation::domain;
use crate::RelationOperators::eval_rel;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::image;
use crate::Set::insert;
use crate::Set::member;

use std::rc::Rc;

pub fn random_el <A> (list: List<A>, random: BigInt) -> A
where
    A : Clone + 'static
{
    nth(list.clone(), modulo_nat((match random.clone().clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }), size_list(list.clone())))
}

pub fn pseudo_allocation <B, A>
    (allocation: Set<(A, Set<B>)>) -> Set<(A, Set<B>)>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    sup_set(image(
        ((Rc::new(move |pair: (A, Set<B>)| -> Set<(A, Set<B>)> {
            product(insert(fst(pair.clone()), bot_set::<A>()), finestpart(snd(pair.clone())))
        })) as Rc<dyn Fn((A, Set<B>)) -> Set<(A, Set<B>)>>),
        allocation.clone()
    ))
}

pub fn to_function_with_fallback_alg <B, A>
    (r: Set<(A, B)>, fallback: B) -> Rc<dyn Fn(A) -> B>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    let fallback_cap = fallback.clone();
    let r_cap = r.clone();
    Rc::new(move |x: A| -> B {
        if member(x.clone(), domain(r_cap.clone())) {
            eval_rel(r_cap.clone(), x.clone())
        } else {
            fallback_cap.clone()
        }
    })
}
