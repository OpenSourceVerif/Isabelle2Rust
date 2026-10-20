use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Natural;
use crate::Arith::Num;
use crate::Arith::one_nat;
use crate::Basis::seq;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::Code_Evaluation::valapp;
use crate::Euclidean_Rings::divide_nat;
use crate::Finite_Set::Finite;
use crate::Fun::comp;
use crate::Fun::id;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::Option::Option;
use crate::Product_Type::Unit;
use crate::Product_Type::scomp;
use crate::Pure::Itself;
use crate::Quickcheck_Exhaustive::FullExhaustive;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::Quickcheck_Narrowing::PartialTermOf;
use crate::Quickcheck_Random::Random;
use crate::String::Literal;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;
use crate::While_Combinator::whilea;

use std::rc::Rc;

#[derive(Clone)]
pub enum StateExt<A, B> {
    StateExt (BigInt, BigInt, BigInt, A, A, B)
}

pub fn lg (x: BigInt) -> BigInt {
    if x.clone() <= one_nat() {
        BigInt::ZERO
    } else {
        one_nat() +
          lg(divide_nat(x.clone(), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })))
    }
}

pub fn l <B, A> (x0: StateExt<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (_, l, _, _, _, _) = x0;
    l.clone()
}

pub fn m <B, A> (x0: StateExt<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (m, _, _, _, _, _) = x0;
    m.clone()
}

pub fn tortoise_update <B, A>
    (tortoisea: Rc<dyn Fn(A) -> A>, x1: StateExt<A, B>) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (tortoisea, StateExt::StateExt (m, l, carrots, hare, tortoise, more)) = (tortoisea,
   x1);
    StateExt::StateExt (m.clone(), l.clone(), carrots.clone(), hare.clone(), (*tortoisea)(tortoise.clone()), more.clone())
}

pub fn carrots_update <B, A>
    (carrotsa: Rc<dyn Fn(BigInt) -> BigInt>,
      x1: StateExt<A, B>) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (carrotsa, StateExt::StateExt (m, l, carrots, hare, tortoise, more)) = (carrotsa,
  x1);
    StateExt::StateExt (m.clone(), l.clone(), (*carrotsa)(carrots.clone()), hare.clone(), tortoise.clone(), more.clone())
}

pub fn hare_update <B, A>
    (harea: Rc<dyn Fn(A) -> A>, x1: StateExt<A, B>) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (harea, StateExt::StateExt (m, l, carrots, hare, tortoise, more)) = (harea,
                                       x1);
    StateExt::StateExt (m.clone(), l.clone(), carrots.clone(), (*harea)(hare.clone()), tortoise.clone(), more.clone())
}

pub fn tortoise <A, B> (x0: StateExt<A, B>) -> A
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (_, _, _, _, tortoise, _) = x0;
    tortoise.clone()
}

pub fn m_update <B, A>
    (ma: Rc<dyn Fn(BigInt) -> BigInt>, x1: StateExt<A, B>) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (ma, StateExt::StateExt (m, l, carrots, hare, tortoise, more)) = (ma,
                                    x1);
    StateExt::StateExt ((*ma)(m.clone()), l.clone(), carrots.clone(), hare.clone(), tortoise.clone(), more.clone())
}

pub fn l_update <B, A>
    (la: Rc<dyn Fn(BigInt) -> BigInt>, x1: StateExt<A, B>) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (la, StateExt::StateExt (m, l, carrots, hare, tortoise, more)) = (la,
                                    x1);
    StateExt::StateExt (m.clone(), (*la)(l.clone()), carrots.clone(), hare.clone(), tortoise.clone(), more.clone())
}

pub fn carrots <B, A> (x0: StateExt<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (_, _, carrots, _, _, _) = x0;
    carrots.clone()
}

pub fn hare <A, B> (x0: StateExt<A, B>) -> A
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (_, _, _, hare, _, _) = x0;
    hare.clone()
}

pub fn brent <A>
    (f: Rc<dyn Fn(A) -> A>,
      x: A) -> Rc<dyn Fn(StateExt<A, Unit>) -> StateExt<A, Unit>>
where
    A : Clone + Finite + Equal + 'static
{
    (({
        let x_cap = x.clone();
        let f_cap = f.clone();
        Rc::new(move |a: StateExt<A, Unit>| -> StateExt<A, Unit> {
            (*comp((({
                let x_capa = x_cap.clone();
                let f_capa = f_cap.clone();
                Rc::new(move |aa: StateExt<A, Unit>| -> StateExt<A, Unit> {
                    (*comp(
                        (({
                            let f_capb = f_capa.clone();
                            Rc::new(move |ab: StateExt<A,
                 Unit>| -> StateExt<A, Unit> {
                                whilea(
                                    ((Rc::new(move |s: StateExt<A,
                          Unit>| -> bool {
                                        ! eq(hare(s.clone()), tortoise(s.clone()))
                                    })) as Rc<dyn Fn(StateExt<A,
                        Unit>) -> bool>),
                                    (({
                                        let f_capc = f_capb.clone();
Rc::new(move |s: StateExt<A, Unit>| -> StateExt<A, Unit> {
    m_update(
        (({
            let s_cap = s.clone();
            Rc::new(move |_: BigInt| -> BigInt {
                m(s_cap.clone()) + one_nat()
            })
        }) as Rc<dyn Fn(BigInt) -> BigInt>),
        hare_update(
            (({
                let s_cap = s.clone();
                let f_capd = f_capc.clone();
                Rc::new(move |_: A| -> A {
                    (*f_capd)(hare(s_cap.clone()))
                })
            }) as Rc<dyn Fn(A) -> A>),
            tortoise_update(
                (({
                    let s_cap = s.clone();
                    let f_capd = f_capc.clone();
                    Rc::new(move |_: A| -> A {
                        (*f_capd)(tortoise(s_cap.clone()))
                    })
                }) as Rc<dyn Fn(A) -> A>),
                s.clone()
            )
        )
    )
})
                                    }) as Rc<dyn Fn(StateExt<A,
                       Unit>) -> StateExt<A, Unit>>),
                                    ab.clone()
                                )
                            })
                        }) as Rc<dyn Fn(StateExt<A,
           Unit>) -> StateExt<A, Unit>>),
                        (({
                            let x_capb = x_capa.clone();
                            let f_capb = f_capa.clone();
                            Rc::new(move |s: StateExt<A,
                Unit>| -> StateExt<A, Unit> {
                                hare_update(
                                    (({
                                        let s_cap = s.clone();
let x_capc = x_capb.clone();
let f_capc = f_capb.clone();
Rc::new(move |_: A| -> A {
    seq(f_capc.clone(), x_capc.clone(), l(s_cap.clone()))
})
                                    }) as Rc<dyn Fn(A) -> A>),
                                    tortoise_update(
                                        (({
    let x_capc = x_capb.clone();
    Rc::new(move |_: A| -> A {
        x_capc.clone()
    })
}) as Rc<dyn Fn(A) -> A>),
m_update(
    ((Rc::new(move |_: BigInt| -> BigInt {
        BigInt::ZERO
    })) as Rc<dyn Fn(BigInt) -> BigInt>),
    s.clone()
)
                                    )
                                )
                            })
                        }) as Rc<dyn Fn(StateExt<A,
           Unit>) -> StateExt<A, Unit>>)
                    ))(aa.clone())
                })
            }) as Rc<dyn Fn(StateExt<A, Unit>) -> StateExt<A,
                     Unit>>), (({
                let x_capa = x_cap.clone();
                let f_capa = f_cap.clone();
                Rc::new(move |aa: StateExt<A, Unit>| -> StateExt<A, Unit> {
                    (*comp(
                        (({
                            let f_capb = f_capa.clone();
                            Rc::new(move |ab: StateExt<A,
                 Unit>| -> StateExt<A, Unit> {
                                whilea(
                                    ((Rc::new(move |s: StateExt<A,
                          Unit>| -> bool {
                                        ! eq(hare(s.clone()), tortoise(s.clone()))
                                    })) as Rc<dyn Fn(StateExt<A,
                        Unit>) -> bool>),
                                    (({
                                        let f_capc = f_capb.clone();
Rc::new(move |ac: StateExt<A, Unit>| -> StateExt<A, Unit> {
    (*comp(
        (({
            let f_capd = f_capc.clone();
            Rc::new(move |s: StateExt<A, Unit>| -> StateExt<A, Unit> {
                l_update(
                    (({
                        let s_cap = s.clone();
                        Rc::new(move |_: BigInt| -> BigInt {
                            l(s_cap.clone()) + one_nat()
                        })
                    }) as Rc<dyn Fn(BigInt) -> BigInt>),
                    hare_update(
                        (({
                            let s_cap = s.clone();
                            let f_cape = f_capd.clone();
                            Rc::new(move |_: A| -> A {
                                (*f_cape)(hare(s_cap.clone()))
                            })
                        }) as Rc<dyn Fn(A) -> A>),
                        s.clone()
                    )
                )
            })
        }) as Rc<dyn Fn(StateExt<A, Unit>) -> StateExt<A, Unit>>),
        ((Rc::new(move |s: StateExt<A, Unit>| -> StateExt<A, Unit> {
            if carrots(s.clone()) == l(s.clone()) {
                l_update(
                    ((Rc::new(move |_: BigInt| -> BigInt {
                        BigInt::ZERO
                    })) as Rc<dyn Fn(BigInt) -> BigInt>),
                    carrots_update(
                        (({
                            let s_cap = s.clone();
                            Rc::new(move |_: BigInt| -> BigInt {
                                (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }) *
                                  carrots(s_cap.clone())
                            })
                        }) as Rc<dyn Fn(BigInt) -> BigInt>),
                        tortoise_update(
                            (({
                                let s_cap = s.clone();
                                Rc::new(move |_: A| -> A {
                                    hare(s_cap.clone())
                                })
                            }) as Rc<dyn Fn(A) -> A>),
                            s.clone()
                        )
                    )
                )
            } else {
                id(s.clone())
            }
        })) as Rc<dyn Fn(StateExt<A, Unit>) -> StateExt<A, Unit>>)
    ))(ac.clone())
})
                                    }) as Rc<dyn Fn(StateExt<A,
                       Unit>) -> StateExt<A, Unit>>),
                                    ab.clone()
                                )
                            })
                        }) as Rc<dyn Fn(StateExt<A,
           Unit>) -> StateExt<A, Unit>>),
                        (({
                            let x_capb = x_capa.clone();
                            let f_capb = f_capa.clone();
                            Rc::new(move |s: StateExt<A,
                Unit>| -> StateExt<A, Unit> {
                                hare_update(
                                    (({
                                        let x_capc = x_capb.clone();
let f_capc = f_capb.clone();
Rc::new(move |_: A| -> A {
    (*f_capc)(x_capc.clone())
})
                                    }) as Rc<dyn Fn(A) -> A>),
                                    tortoise_update(
                                        (({
    let x_capc = x_capb.clone();
    Rc::new(move |_: A| -> A {
        x_capc.clone()
    })
}) as Rc<dyn Fn(A) -> A>),
l_update(
    ((Rc::new(move |_: BigInt| -> BigInt {
        one_nat()
    })) as Rc<dyn Fn(BigInt) -> BigInt>),
    carrots_update(
        ((Rc::new(move |_: BigInt| -> BigInt {
            one_nat()
        })) as Rc<dyn Fn(BigInt) -> BigInt>),
        s.clone()
    )
)
                                    )
                                )
                            })
                        }) as Rc<dyn Fn(StateExt<A,
           Unit>) -> StateExt<A, Unit>>)
                    ))(aa.clone())
                })
            }) as Rc<dyn Fn(StateExt<A, Unit>) -> StateExt<A,
                     Unit>>)))(a.clone())
        })
    }) as Rc<dyn Fn(StateExt<A, Unit>) -> StateExt<A, Unit>>)
}

pub fn make <A>
    (m: BigInt, l: BigInt, carrots: BigInt, hare: A,
      tortoise: A) -> StateExt<A, Unit>
where
    A : Clone + 'static
{
    StateExt::StateExt (m.clone(), l.clone(), carrots.clone(), hare.clone(), tortoise.clone(), Unit::Unity)
}

pub fn more <B, A> (x0: StateExt<A, B>) -> B
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (_, _, _, _, _, more) = x0;
    more.clone()
}

pub fn extend <B, A> (r: StateExt<A, Unit>, more: B) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    StateExt::StateExt (m(r.clone()), l(r.clone()), carrots(r.clone()), hare(r.clone()), tortoise(r.clone()), more.clone())
}

pub fn fields <A>
    (m: BigInt, l: BigInt, carrots: BigInt, hare: A,
      tortoise: A) -> StateExt<A, Unit>
where
    A : Clone + 'static
{
    StateExt::StateExt (m.clone(), l.clone(), carrots.clone(), hare.clone(), tortoise.clone(), Unit::Unity)
}

pub fn truncate <A, B> (r: StateExt<A, B>) -> StateExt<A, Unit>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    StateExt::StateExt (m(r.clone()), l(r.clone()), carrots(r.clone()), hare(r.clone()), tortoise(r.clone()), Unit::Unity)
}

pub fn more_update <A, B>
    (morea: Rc<dyn Fn(A) -> A>, x1: StateExt<B, A>) -> StateExt<B, A>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (morea, StateExt::StateExt (m, l, carrots, hare, tortoise, more)) = (morea,
                                       x1);
    StateExt::StateExt (m.clone(), l.clone(), carrots.clone(), hare.clone(), tortoise.clone(), (*morea)(more.clone()))
}
