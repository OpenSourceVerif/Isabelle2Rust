use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Minus;
use crate::Arith::One;
use crate::Enum::Enum;
use crate::Finite_Set::card;
use crate::HOL::Equal;
use crate::HOL::all;
use crate::HOL::implies;
use crate::Product_Type::fst;
use crate::Product_Type::product;
use crate::Product_Type::snd;
use crate::Relation::domain;
use crate::Relation::image;
use crate::Relation::rangea;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::inf_set;
use crate::Set::insert;
use crate::Set::sup_set;
use crate::Set::the_elem;
use crate::SetUtils::trivial;

use std::rc::Rc;

pub fn flip <A, B> (tup: (A, B)) -> (B, A)
where
    A : Clone + 'static,
    B : Clone + 'static
{
    (snd(tup.clone()), fst(tup.clone()))
}

pub fn outside <B, A> (r: Set<(A, B)>, x: Set<A>) -> Set<(A, B)>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    <Set<(A, B)> as Minus>::minus(r.clone(), product(x.clone(), rangea(r.clone())))
}

pub fn paste <B, A> (p: Set<(A, B)>, q: Set<(A, B)>) -> Set<(A, B)>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    sup_set(outside(p.clone(), domain(q.clone())), q.clone())
}

pub fn runiq <B, A> (r: Set<(A, B)>) -> bool
where
    A : Clone + Enum + Equal + 'static,
    B : Clone + Equal + 'static
{
    all(
        (({
            let r_cap = r.clone();
            Rc::new(move |x: Set<A>| -> bool {
                implies(trivial(x.clone()), trivial(image(r_cap.clone(), x.clone())))
            })
        }) as Rc<dyn Fn(Set<A>) -> bool>)
    )
}

pub fn eval_rel <B, A> (r: Set<(A, B)>, a: A) -> B
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    the_elem(image(r.clone(), insert(a.clone(), bot_set::<A>())))
}

pub fn restrict <B, A> (r: Set<(A, B)>, x: Set<A>) -> Set<(A, B)>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    inf_set(product(x.clone(), rangea(r.clone())), r.clone())
}

pub fn eval_rel_or <B, A> (r: Set<(A, B)>, a: A, z: B) -> B
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    let im = image(r.clone(), insert(a.clone(), bot_set::<A>()));
    if card(im.clone()) == <BigInt as One>::one() {
        the_elem(im.clone())
    } else {
        z.clone()
    }
}
