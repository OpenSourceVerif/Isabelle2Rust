use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::one_nat;
use crate::Complete_Lattices::sup_set;
use crate::Euclidean_Rings::divide_nat;
use crate::Finite_Set::Finite;
use crate::Finite_Set::card;
use crate::Finite_Set::finite;
use crate::Groups_Big::sum;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::HOL::implies;
use crate::Product_Type::fst;
use crate::Product_Type::snd;
use crate::Set::Set;
use crate::Set::ball;
use crate::Set::bot_set;
use crate::Set::filter;
use crate::Set::image;
use crate::Set::insert;
use crate::Set::less_eq_set;
use crate::Set::member;

use std::rc::Rc;

pub fn n <A> (v: Set<A>, l: Rc<dyn Fn(A) -> BigInt>, i: BigInt) -> BigInt
where
    A : Clone + Equal + 'static
{
    card(filter(
        (({
            let i_cap = i.clone();
            let l_cap = l.clone();
            Rc::new(move |va: A| -> bool {
                (*l_cap)(va.clone()) == i_cap.clone()
            })
        }) as Rc<dyn Fn(A) -> bool>),
        v.clone()
    ))
}

pub fn osc <A> (l: Rc<dyn Fn(A) -> BigInt>, e: Set<(A, A)>) -> bool
where
    A : Clone + 'static
{
    ball(
        e.clone(),
        (({
            let l_cap = l.clone();
            Rc::new(move |ea: (A, A)| -> bool {
                (*l_cap)(fst(ea.clone())) == one_nat() ||
                  ((*l_cap)(snd(ea.clone())) == one_nat() ||
                    (*l_cap)(fst(ea.clone())) == (*l_cap)(snd(ea.clone())) &&
                      one_nat() < (*l_cap)(fst(ea.clone())))
            })
        }) as Rc<dyn Fn((A, A)) -> bool>)
    )
}

pub fn edge_as_set <A> (e: (A, A)) -> Set<A>
where
    A : Clone + Equal + 'static
{
    insert(fst(e.clone()), insert(snd(e.clone()), bot_set::<A>()))
}

pub fn matching_i <A>
    (i: BigInt, x1: Set<A>, x2: Set<(A, A)>, m: Set<(A, A)>,
      l: Rc<dyn Fn(A) -> BigInt>) -> Set<(A, A)>
where
    A : Clone + 'static
{
    filter(
        (({
            let l_cap = l.clone();
            let i_cap = i.clone();
            Rc::new(move |ea: (A, A)| -> bool {
                i_cap.clone() == one_nat() &&
                  ((*l_cap)(fst(ea.clone())) == i_cap.clone() ||
                    (*l_cap)(snd(ea.clone())) == i_cap.clone()) ||
                  one_nat() < i_cap.clone() &&
                    ((*l_cap)(fst(ea.clone())) == i_cap.clone() &&
                      (*l_cap)(snd(ea.clone())) == i_cap.clone())
            })
        }) as Rc<dyn Fn((A, A)) -> bool>),
        m.clone()
    )
}

pub fn v_i <A>
    (i: BigInt, v: Set<A>, e: Set<(A, A)>, m: Set<(A, A)>,
      l: Rc<dyn Fn(A) -> BigInt>) -> Set<A>
where
    A : Clone + Equal + 'static
{
    sup_set(image(((Rc::new(move |a: (A, A)| -> Set<A> {
        edge_as_set(a.clone())
    })) as Rc<dyn Fn((A, A)) -> Set<A>>), matching_i(i.clone(), v.clone(), e.clone(), m.clone(), l.clone())))
}

pub fn degree <A> (e: Set<(A, A)>, v: A) -> BigInt
where
    A : Clone + Equal + 'static
{
    card(filter(
        (({
            let v_cap = v.clone();
            Rc::new(move |ea: (A, A)| -> bool {
                eq(fst(ea.clone()), v_cap.clone()) ||
                  eq(snd(ea.clone()), v_cap.clone())
            })
        }) as Rc<dyn Fn((A, A)) -> bool>),
        e.clone()
    ))
}

pub fn weight (lv: Set<BigInt>, f: Rc<dyn Fn(BigInt) -> BigInt>) -> BigInt {
    (*f)(one_nat()) +
      sum(
          (({
              let f_cap = f.clone();
              Rc::new(move |i: BigInt| -> BigInt {
                  divide_nat((*f_cap)(i.clone()), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }))
              })
          }) as Rc<dyn Fn(BigInt) -> BigInt>),
          lv.clone()
      )
}

pub fn disjoint_edges <A> (e1: (A, A), e2: (A, A)) -> bool
where
    A : Clone + Equal + 'static
{
    ! eq(fst(e1.clone()), fst(e2.clone())) &&
      (! eq(fst(e1.clone()), snd(e2.clone())) &&
        (! eq(snd(e1.clone()), fst(e2.clone())) &&
          ! eq(snd(e1.clone()), snd(e2.clone()))))
}

pub fn finite_graph <A> (v: Set<A>, e: Set<(A, A)>) -> bool
where
    A : Clone + Finite + Equal + 'static
{
    finite(v.clone()) &&
      (finite(e.clone()) &&
        ball(
            e.clone(),
            (({
                let v_cap = v.clone();
                Rc::new(move |ea: (A, A)| -> bool {
                    member(fst(ea.clone()), v_cap.clone()) &&
                      (member(snd(ea.clone()), v_cap.clone()) &&
                        ! eq(fst(ea.clone()), snd(ea.clone())))
                })
            }) as Rc<dyn Fn((A, A)) -> bool>)
        ))
}

pub fn matching <A> (v: Set<A>, e: Set<(A, A)>, m: Set<(A, A)>) -> bool
where
    A : Clone + Finite + Equal + 'static
{
    less_eq_set(m.clone(), e.clone()) &&
      (finite_graph(v.clone(), e.clone()) &&
        ball(
            m.clone(),
            (({
                let m_cap = m.clone();
                Rc::new(move |e1: (A, A)| -> bool {
                    ball(
                        m_cap.clone(),
                        (({
                            let e1_cap = e1.clone();
                            Rc::new(move |e2: (A, A)| -> bool {
                                implies(! <(A, A) as Equal>::equal(e1_cap.clone(), e2.clone()), disjoint_edges(e1_cap.clone(), e2.clone()))
                            })
                        }) as Rc<dyn Fn((A, A)) -> bool>)
                    )
                })
            }) as Rc<dyn Fn((A, A)) -> bool>)
        ))
}

pub fn endpoint_inv <A> (v: Set<A>, e: (A, A)) -> A
where
    A : Clone + Equal + 'static
{
    if member(fst(e.clone()), v.clone()) {
        fst(e.clone())
    } else {
        snd(e.clone())
    }
}

pub fn relevant_endpoint <A>
    (l: Rc<dyn Fn(A) -> BigInt>, x1: Set<A>, e: (A, A)) -> A
where
    A : Clone + 'static
{
    if (*l)(fst(e.clone())) == one_nat() {
        fst(e.clone())
    } else {
        snd(e.clone())
    }
}
