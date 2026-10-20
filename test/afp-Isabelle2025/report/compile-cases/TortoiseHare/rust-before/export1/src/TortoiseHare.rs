use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Natural;
use crate::Arith::one_nat;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::Code_Evaluation::valapp;
use crate::Finite_Set::Finite;
use crate::Fun::comp;
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

use std::marker::PhantomData;

use std::rc::Rc;

#[derive(Clone)]
pub enum StateExt<A, B> {
    StateExt (BigInt, BigInt, BigInt, A, A, B)
}

pub fn l <B, A> (x0: StateExt<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (_, _, l, _, _, _) = x0;
    l.clone()
}

pub fn m <B, A> (x0: StateExt<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (_, m, _, _, _, _) = x0;
    m.clone()
}

pub fn nu <B, A> (x0: StateExt<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (nu, _, _, _, _, _) = x0;
    nu.clone()
}

pub fn hare <A, B> (x0: StateExt<A, B>) -> A
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (_, _, _, hare, _, _) = x0;
    hare.clone()
}

pub fn make <A>
    (nu: BigInt, m: BigInt, l: BigInt, hare: A,
      tortoise: A) -> StateExt<A, Unit>
where
    A : Clone + 'static
{
    StateExt::StateExt (nu.clone(), m.clone(), l.clone(), hare.clone(), tortoise.clone(), Unit::Unity)
}

pub fn more <B, A> (x0: StateExt<A, B>) -> B
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (_, _, _, _, _, more) = x0;
    more.clone()
}

pub fn tortoise <A, B> (x0: StateExt<A, B>) -> A
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let StateExt::StateExt (_, _, _, _, tortoise, _) = x0;
    tortoise.clone()
}

pub fn extend <B, A> (r: StateExt<A, Unit>, more: B) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    StateExt::StateExt (nu(r.clone()), m(r.clone()), l(r.clone()), hare(r.clone()), tortoise(r.clone()), more.clone())
}

pub fn fields <A>
    (nu: BigInt, m: BigInt, l: BigInt, hare: A,
      tortoise: A) -> StateExt<A, Unit>
where
    A : Clone + 'static
{
    StateExt::StateExt (nu.clone(), m.clone(), l.clone(), hare.clone(), tortoise.clone(), Unit::Unity)
}

pub fn l_update <B, A>
    (la: Rc<dyn Fn(BigInt) -> BigInt>, x1: StateExt<A, B>) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (la, StateExt::StateExt (nu, m, l, hare, tortoise, more)) = (la, x1);
    StateExt::StateExt (nu.clone(), m.clone(), (*la)(l.clone()), hare.clone(), tortoise.clone(), more.clone())
}

pub fn m_update <B, A>
    (ma: Rc<dyn Fn(BigInt) -> BigInt>, x1: StateExt<A, B>) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (ma, StateExt::StateExt (nu, m, l, hare, tortoise, more)) = (ma, x1);
    StateExt::StateExt (nu.clone(), (*ma)(m.clone()), l.clone(), hare.clone(), tortoise.clone(), more.clone())
}

pub fn truncate <A, B> (r: StateExt<A, B>) -> StateExt<A, Unit>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    StateExt::StateExt (nu(r.clone()), m(r.clone()), l(r.clone()), hare(r.clone()), tortoise(r.clone()), Unit::Unity)
}

pub fn nu_update <B, A>
    (nua: Rc<dyn Fn(BigInt) -> BigInt>, x1: StateExt<A, B>) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (nua, StateExt::StateExt (nu, m, l, hare, tortoise, more)) = (nua, x1);
    StateExt::StateExt ((*nua)(nu.clone()), m.clone(), l.clone(), hare.clone(), tortoise.clone(), more.clone())
}

pub fn tortoise_update <B, A>
    (tortoisea: Rc<dyn Fn(A) -> A>, x1: StateExt<A, B>) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (tortoisea, StateExt::StateExt (nu, m, l, hare, tortoise, more)) = (tortoisea,
                                      x1);
    StateExt::StateExt (nu.clone(), m.clone(), l.clone(), hare.clone(), (*tortoisea)(tortoise.clone()), more.clone())
}

pub fn hare_update <B, A>
    (harea: Rc<dyn Fn(A) -> A>, x1: StateExt<A, B>) -> StateExt<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (harea, StateExt::StateExt (nu, m, l, hare, tortoise, more)) = (harea,
                                  x1);
    StateExt::StateExt (nu.clone(), m.clone(), l.clone(), (*harea)(hare.clone()), tortoise.clone(), more.clone())
}

pub fn tortoise_hare <A>
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
                let f_capd = f_capc.clone();
                Rc::new(move |_: A| -> A {
                    (*f_capd)(hare(s_cap.clone()))
                })
            }) as Rc<dyn Fn(A) -> A>),
            s.clone()
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
                            let f_capb = f_capa.clone();
                            Rc::new(move |s: StateExt<A,
                Unit>| -> StateExt<A, Unit> {
                                hare_update(
                                    (({
                                        let s_cap = s.clone();
let f_capc = f_capb.clone();
Rc::new(move |_: A| -> A {
    (*f_capc)(tortoise(s_cap.clone()))
})
                                    }) as Rc<dyn Fn(A) -> A>),
                                    l_update(
                                        ((Rc::new(move |_: BigInt| -> BigInt {
    one_nat()
})) as Rc<dyn Fn(BigInt) -> BigInt>),
s.clone()
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
                    (*comp((({
                        let x_capb = x_capa.clone();
                        let f_capb = f_capa.clone();
                        Rc::new(move |ab: StateExt<A,
             Unit>| -> StateExt<A, Unit> {
                            (*comp(
                                (({
                                    let f_capc = f_capb.clone();
                                    Rc::new(move |ac: StateExt<A,
                         Unit>| -> StateExt<A, Unit> {
                                        whilea(
    ((Rc::new(move |s: StateExt<A, Unit>| -> bool {
        ! eq(hare(s.clone()), tortoise(s.clone()))
    })) as Rc<dyn Fn(StateExt<A, Unit>) -> bool>),
    (({
        let f_capd = f_capc.clone();
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
                        let f_cape = f_capd.clone();
                        Rc::new(move |_: A| -> A {
                            (*f_cape)(hare(s_cap.clone()))
                        })
                    }) as Rc<dyn Fn(A) -> A>),
                    tortoise_update(
                        (({
                            let s_cap = s.clone();
                            let f_cape = f_capd.clone();
                            Rc::new(move |_: A| -> A {
                                (*f_cape)(tortoise(s_cap.clone()))
                            })
                        }) as Rc<dyn Fn(A) -> A>),
                        s.clone()
                    )
                )
            )
        })
    }) as Rc<dyn Fn(StateExt<A, Unit>) -> StateExt<A, Unit>>),
    ac.clone()
)
                                    })
                                }) as Rc<dyn Fn(StateExt<A,
                   Unit>) -> StateExt<A, Unit>>),
                                (({
                                    let x_capc = x_capb.clone();
                                    Rc::new(move |s: StateExt<A,
                        Unit>| -> StateExt<A, Unit> {
                                        tortoise_update(
    (({
        let x_capd = x_capc.clone();
        Rc::new(move |_: A| -> A {
            x_capd.clone()
        })
    }) as Rc<dyn Fn(A) -> A>),
    m_update(
        ((Rc::new(move |_: BigInt| -> BigInt {
            BigInt::ZERO
        })) as Rc<dyn Fn(BigInt) -> BigInt>),
        s.clone()
    )
)
                                    })
                                }) as Rc<dyn Fn(StateExt<A,
                   Unit>) -> StateExt<A, Unit>>)
                            ))(ab.clone())
                        })
                    }) as Rc<dyn Fn(StateExt<A,
       Unit>) -> StateExt<A, Unit>>), (({
                        let x_capb = x_capa.clone();
                        let f_capb = f_capa.clone();
                        Rc::new(move |ab: StateExt<A,
             Unit>| -> StateExt<A, Unit> {
                            (*comp(
                                (({
                                    let f_capc = f_capb.clone();
                                    Rc::new(move |ac: StateExt<A,
                         Unit>| -> StateExt<A, Unit> {
                                        whilea(
    ((Rc::new(move |s: StateExt<A, Unit>| -> bool {
        ! eq(hare(s.clone()), tortoise(s.clone()))
    })) as Rc<dyn Fn(StateExt<A, Unit>) -> bool>),
    (({
        let f_capd = f_capc.clone();
        Rc::new(move |s: StateExt<A, Unit>| -> StateExt<A, Unit> {
            hare_update(
                (({
                    let s_cap = s.clone();
                    let f_cape = f_capd.clone();
                    Rc::new(move |_: A| -> A {
                        (*f_cape)((*f_cape)(hare(s_cap.clone())))
                    })
                }) as Rc<dyn Fn(A) -> A>),
                tortoise_update(
                    (({
                        let s_cap = s.clone();
                        let f_cape = f_capd.clone();
                        Rc::new(move |_: A| -> A {
                            (*f_cape)(tortoise(s_cap.clone()))
                        })
                    }) as Rc<dyn Fn(A) -> A>),
                    nu_update(
                        (({
                            let s_cap = s.clone();
                            Rc::new(move |_: BigInt| -> BigInt {
                                nu(s_cap.clone()) + one_nat()
                            })
                        }) as Rc<dyn Fn(BigInt) -> BigInt>),
                        s.clone()
                    )
                )
            )
        })
    }) as Rc<dyn Fn(StateExt<A, Unit>) -> StateExt<A, Unit>>),
    ac.clone()
)
                                    })
                                }) as Rc<dyn Fn(StateExt<A,
                   Unit>) -> StateExt<A, Unit>>),
                                (({
                                    let x_capc = x_capb.clone();
                                    let f_capc = f_capb.clone();
                                    Rc::new(move |s: StateExt<A,
                        Unit>| -> StateExt<A, Unit> {
                                        hare_update(
    (({
        let x_capd = x_capc.clone();
        let f_capd = f_capc.clone();
        Rc::new(move |_: A| -> A {
            (*f_capd)((*f_capd)(x_capd.clone()))
        })
    }) as Rc<dyn Fn(A) -> A>),
    tortoise_update(
        (({
            let x_capd = x_capc.clone();
            let f_capd = f_capc.clone();
            Rc::new(move |_: A| -> A {
                (*f_capd)(x_capd.clone())
            })
        }) as Rc<dyn Fn(A) -> A>),
        nu_update(
            ((Rc::new(move |_: BigInt| -> BigInt {
                one_nat()
            })) as Rc<dyn Fn(BigInt) -> BigInt>),
            s.clone()
        )
    )
)
                                    })
                                }) as Rc<dyn Fn(StateExt<A,
                   Unit>) -> StateExt<A, Unit>>)
                            ))(ab.clone())
                        })
                    }) as Rc<dyn Fn(StateExt<A,
       Unit>) -> StateExt<A, Unit>>)))(aa.clone())
                })
            }) as Rc<dyn Fn(StateExt<A, Unit>) -> StateExt<A,
                     Unit>>)))(a.clone())
        })
    }) as Rc<dyn Fn(StateExt<A, Unit>) -> StateExt<A, Unit>>)
}

pub fn more_update <A, B>
    (morea: Rc<dyn Fn(A) -> A>, x1: StateExt<B, A>) -> StateExt<B, A>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    let (morea, StateExt::StateExt (nu, m, l, hare, tortoise, more)) = (morea,
                                  x1);
    StateExt::StateExt (nu.clone(), m.clone(), l.clone(), hare.clone(), tortoise.clone(), (*morea)(more.clone()))
}

impl <A : Clone + Equal + 'static,  B : Clone + Equal + 'static> Equal for
    StateExt<A, B> {
    fn equal (x0: StateExt<A, B>, x1: StateExt<A, B>) -> bool {
        let (StateExt::StateExt (nua, ma, la, harea, tortoisea, morea), StateExt::StateExt (nu, m, l, hare, tortoise, more)) = (x0,
          x1);
        nua.clone() == nu.clone() &&
          (ma.clone() == m.clone() &&
            (la.clone() == l.clone() &&
              (eq(harea.clone(), hare.clone()) &&
                (eq(tortoisea.clone(), tortoise.clone()) &&
                  eq(morea.clone(), more.clone())))))
    }
}

impl <A : Clone + Typerep + Random + 'static, 
       B : Clone + Typerep + Random + 'static>
    Random for StateExt<A, B> {
    fn random
        (i: Natural,
          eta_arg_0: (Natural, Natural)) -> ((StateExt<A,
                 B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
        (*scomp(
            (({
                let i_cap = i.clone();
                Rc::new(move |a: (Natural, Natural)| -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                    <BigInt as Random>::random(i_cap.clone(), a.clone())
                })
            }) as Rc<dyn Fn((Natural, Natural)) -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
            (({
                let i_cap = i.clone();
                Rc::new(move |x: (BigInt, Rc<dyn Fn(Unit) -> Term>), eta_arg: (Natural, Natural)| -> ((StateExt<A,
                                  B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                    (*scomp(
                        (({
                            let i_capa = i_cap.clone();
                            Rc::new(move |a: (Natural, Natural)| -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                                <BigInt as Random>::random(i_capa.clone(), a.clone())
                            })
                        }) as Rc<dyn Fn((Natural, Natural)) -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
                        (({
                            let x_cap = x.clone();
                            let i_capa = i_cap.clone();
                            Rc::new(move |y: (BigInt, Rc<dyn Fn(Unit) -> Term>), eta_arh: (Natural, Natural)| -> ((StateExt<A,
      B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                                (*scomp(
                                    (({
                                        let i_capb = i_capa.clone();
Rc::new(move |a: (Natural, Natural)| -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
    <BigInt as Random>::random(i_capb.clone(), a.clone())
})
                                    }) as Rc<dyn Fn((Natural, Natural)) -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
                                    (({
                                        let y_cap = y.clone();
let x_capa = x_cap.clone();
let i_capb = i_capa.clone();
Rc::new(move |z: (BigInt, Rc<dyn Fn(Unit) -> Term>), eta_ari: (Natural, Natural)| -> ((StateExt<A,
                  B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
    (*scomp(
        (({
            let i_capc = i_capb.clone();
            Rc::new(move |a: (Natural, Natural)| -> ((A, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                <A as Random>::random(i_capc.clone(), a.clone())
            })
        }) as Rc<dyn Fn((Natural, Natural)) -> ((A, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
        (({
            let z_cap = z.clone();
            let y_capa = y_cap.clone();
            let x_capb = x_capa.clone();
            let i_capc = i_capb.clone();
            Rc::new(move |aa: (A, Rc<dyn Fn(Unit) -> Term>), eta_arj: (Natural, Natural)| -> ((StateExt<A,
                          B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                (*scomp(
                    (({
                        let i_capd = i_capc.clone();
                        Rc::new(move |a: (Natural, Natural)| -> ((A, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                            <A as Random>::random(i_capd.clone(), a.clone())
                        })
                    }) as Rc<dyn Fn((Natural, Natural)) -> ((A, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
                    (({
                        let aa_cap = aa.clone();
                        let z_capa = z_cap.clone();
                        let y_capb = y_capa.clone();
                        let x_capc = x_capb.clone();
                        let i_capd = i_capc.clone();
                        Rc::new(move |ab: (A, Rc<dyn Fn(Unit) -> Term>), eta_ark: (Natural, Natural)| -> ((StateExt<A,
                                      B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                            (*scomp(
                                (({
                                    let i_cape = i_capd.clone();
                                    Rc::new(move |a: (Natural, Natural)| -> ((B, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                                        <B as Random>::random(i_cape.clone(), a.clone())
                                    })
                                }) as Rc<dyn Fn((Natural, Natural)) -> ((B, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
                                (({
                                    let ab_cap = ab.clone();
                                    let aa_capa = aa_cap.clone();
                                    let z_capb = z_capa.clone();
                                    let y_capc = y_capb.clone();
                                    let x_capd = x_capc.clone();
                                    Rc::new(move |ac: (B, Rc<dyn Fn(Unit) -> Term>), eta_arl: (Natural, Natural)| -> ((StateExt<A,
          B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                                        (valapp(valapp(valapp(valapp(valapp(valapp((
    ((Rc::new(move |boundary_arg: BigInt| {
        (({
            let boundary_arg_cap = boundary_arg.clone();
            Rc::new(move |boundary_arh: BigInt| {
                (({
                    let boundary_arh_cap = boundary_arh.clone();
                    let boundary_arg_capa = boundary_arg_cap.clone();
                    Rc::new(move |boundary_ari: BigInt| {
                        (({
                            let boundary_ari_cap = boundary_ari.clone();
                            let boundary_arh_capa = boundary_arh_cap.clone();
                            let boundary_arg_capb = boundary_arg_capa.clone();
                            Rc::new(move |boundary_arj: A| {
                                (({
                                    let boundary_arj_cap = boundary_arj.clone();
                                    let boundary_ari_capa = boundary_ari_cap.clone();
                                    let boundary_arh_capb = boundary_arh_capa.clone();
                                    let boundary_arg_capc = boundary_arg_capb.clone();
                                    Rc::new(move |boundary_ark: A| {
                                        (({
    let boundary_ark_cap = boundary_ark.clone();
    let boundary_arj_capa = boundary_arj_cap.clone();
    let boundary_ari_capb = boundary_ari_capa.clone();
    let boundary_arh_capc = boundary_arh_capb.clone();
    let boundary_arg_capd = boundary_arg_capc.clone();
    Rc::new(move |boundary_arl: B| -> StateExt<A, B> {
        (*{
            let boundary_arj_capb = boundary_arj_capa.clone();
            let boundary_ari_capc = boundary_ari_capb.clone();
            let boundary_arh_capd = boundary_arh_capc.clone();
            let boundary_arg_cape = boundary_arg_capd.clone();
            Rc::new(move |boundary_arka: A, boundary_arla: B| {
                (*{
                    let boundary_ari_capd = boundary_ari_capc.clone();
                    let boundary_arh_cape = boundary_arh_capd.clone();
                    let boundary_arg_capf = boundary_arg_cape.clone();
                    Rc::new(move |boundary_arja: A, boundary_arkb: A, boundary_arlb: B| {
                        (*{
                            let boundary_arh_capf = boundary_arh_cape.clone();
                            let boundary_arg_capg = boundary_arg_capf.clone();
                            Rc::new(move |boundary_aria: BigInt, boundary_arjb: A, boundary_arkc: A, boundary_arlc: B| {
                                (*{
                                    let boundary_arg_caph = boundary_arg_capg.clone();
                                    Rc::new(move |boundary_arha: BigInt, boundary_arib: BigInt, boundary_arjc: A, boundary_arkd: A, boundary_arld: B| {
                                        StateExt::StateExt (boundary_arg_caph.clone(), boundary_arha.clone(), boundary_arib.clone(), boundary_arjc.clone(), boundary_arkd.clone(), boundary_arld.clone())
                                    })
                                })(boundary_arh_capf.clone(), boundary_aria.clone(), boundary_arjb.clone(), boundary_arkc.clone(), boundary_arlc.clone())
                            })
                        })(boundary_ari_capd.clone(), boundary_arja.clone(), boundary_arkb.clone(), boundary_arlb.clone())
                    })
                })(boundary_arj_capb.clone(), boundary_arka.clone(), boundary_arla.clone())
            })
        })(boundary_ark_cap.clone(), boundary_arl.clone())
    })
}) as Rc<dyn Fn(B) -> StateExt<A, B>>)
                                    })
                                }) as Rc<dyn Fn(A) -> Rc<dyn Fn(B) -> StateExt<A,
 B>>>)
                            })
                        }) as Rc<dyn Fn(A) -> Rc<dyn Fn(A) -> Rc<dyn Fn(B) -> StateExt<A,
         B>>>>)
                    })
                }) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(A) -> Rc<dyn Fn(A) -> Rc<dyn Fn(B) -> StateExt<A,
                      B>>>>>)
            })
        }) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(BigInt) -> Rc<dyn Fn(A) -> Rc<dyn Fn(A) -> Rc<dyn Fn(B) -> StateExt<A,
                                   B>>>>>>)
    })) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(BigInt) -> Rc<dyn Fn(BigInt) -> Rc<dyn Fn(A) -> Rc<dyn Fn(A) -> Rc<dyn Fn(B) -> StateExt<A,
             B>>>>>>>),
    ((Rc::new(move |_: Unit| -> Term {
        Term::Const (Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))
    })) as Rc<dyn Fn(Unit) -> Term>)
), x_capd.clone()), y_capc.clone()), z_capb.clone()), aa_capa.clone()), ab_cap.clone()), ac.clone()), eta_arl.clone())
                                    })
                                }) as Rc<dyn Fn((B, Rc<dyn Fn(Unit) -> Term>),
         (Natural, Natural)) -> ((StateExt<A,
     B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
                            ))(eta_ark.clone())
                        })
                    }) as Rc<dyn Fn((A, Rc<dyn Fn(Unit) -> Term>),
                                     (Natural, Natural)) -> ((StateExt<A,
                                 B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
                ))(eta_arj.clone())
            })
        }) as Rc<dyn Fn((A, Rc<dyn Fn(Unit) -> Term>),
                         (Natural, Natural)) -> ((StateExt<A,
                     B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
    ))(eta_ari.clone())
})
                                    }) as Rc<dyn Fn((BigInt, Rc<dyn Fn(Unit) -> Term>),
             (Natural, Natural)) -> ((StateExt<A,
         B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
                                ))(eta_arh.clone())
                            })
                        }) as Rc<dyn Fn((BigInt, Rc<dyn Fn(Unit) -> Term>),
 (Natural, Natural)) -> ((StateExt<A, B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
                    ))(eta_arg.clone())
                })
            }) as Rc<dyn Fn((BigInt, Rc<dyn Fn(Unit) -> Term>),
                             (Natural, Natural)) -> ((StateExt<A,
                         B>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
        ))(eta_arg_0.clone())
    }
}

impl <A : Clone + Typerep + TermOf + 'static, 
       B : Clone + Typerep + TermOf + 'static>
    TermOf for StateExt<A, B> {
    fn term_of (x0: StateExt<A, B>) -> Term {
        let StateExt::StateExt (a, b, c, d, e, f) = x0;
        Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::Const (Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))), Box::new(<BigInt as TermOf>::term_of(a.clone())))), Box::new(<BigInt as TermOf>::term_of(b.clone())))), Box::new(<BigInt as TermOf>::term_of(c.clone())))), Box::new(<A as TermOf>::term_of(d.clone())))), Box::new(<A as TermOf>::term_of(e.clone())))), Box::new(<B as TermOf>::term_of(f.clone())))
    }
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static> Typerep for
    StateExt<A, B> {
    fn typerep (x0: Itself<StateExt<A, B>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil))))))
    }
}

impl <A : Clone + TermOf + Typerep + FullExhaustive + 'static, 
       B : Clone + TermOf + Typerep + FullExhaustive + 'static>
    FullExhaustive for StateExt<A, B> {
    fn full_exhaustive
        (f: Rc<dyn Fn((StateExt<A, B>, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>,
          i: Natural) -> Option<(bool, List<Term>)> {
        <BigInt as FullExhaustive>::full_exhaustive(
            (({
                let i_cap = i.clone();
                let f_cap = f.clone();
                Rc::new(move |x: (BigInt, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
                    <BigInt as FullExhaustive>::full_exhaustive(
                        (({
                            let i_capa = i_cap.clone();
                            let x_cap = x.clone();
                            let f_capa = f_cap.clone();
                            Rc::new(move |y: (BigInt, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
                                <BigInt as FullExhaustive>::full_exhaustive(
                                    (({
                                        let i_capb = i_capa.clone();
let y_cap = y.clone();
let x_capa = x_cap.clone();
let f_capb = f_capa.clone();
Rc::new(move |z: (BigInt, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
    <A as FullExhaustive>::full_exhaustive(
        (({
            let i_capc = i_capb.clone();
            let z_cap = z.clone();
            let y_capa = y_cap.clone();
            let x_capb = x_capa.clone();
            let f_capc = f_capb.clone();
            Rc::new(move |aa: (A, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
                <A as FullExhaustive>::full_exhaustive(
                    (({
                        let i_capd = i_capc.clone();
                        let aa_cap = aa.clone();
                        let z_capa = z_cap.clone();
                        let y_capb = y_capa.clone();
                        let x_capc = x_capb.clone();
                        let f_capd = f_capc.clone();
                        Rc::new(move |ab: (A, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
                            <B as FullExhaustive>::full_exhaustive(
                                (({
                                    let ab_cap = ab.clone();
                                    let aa_capa = aa_cap.clone();
                                    let z_capb = z_capa.clone();
                                    let y_capc = y_capb.clone();
                                    let x_capd = x_capc.clone();
                                    let f_cape = f_capd.clone();
                                    Rc::new(move |ac: (B, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
                                        (*f_cape)(valapp(valapp(valapp(valapp(valapp(valapp((
    ((Rc::new(move |boundary_arg: BigInt| {
        (({
            let boundary_arg_cap = boundary_arg.clone();
            Rc::new(move |boundary_arh: BigInt| {
                (({
                    let boundary_arh_cap = boundary_arh.clone();
                    let boundary_arg_capa = boundary_arg_cap.clone();
                    Rc::new(move |boundary_ari: BigInt| {
                        (({
                            let boundary_ari_cap = boundary_ari.clone();
                            let boundary_arh_capa = boundary_arh_cap.clone();
                            let boundary_arg_capb = boundary_arg_capa.clone();
                            Rc::new(move |boundary_arj: A| {
                                (({
                                    let boundary_arj_cap = boundary_arj.clone();
                                    let boundary_ari_capa = boundary_ari_cap.clone();
                                    let boundary_arh_capb = boundary_arh_capa.clone();
                                    let boundary_arg_capc = boundary_arg_capb.clone();
                                    Rc::new(move |boundary_ark: A| {
                                        (({
    let boundary_ark_cap = boundary_ark.clone();
    let boundary_arj_capa = boundary_arj_cap.clone();
    let boundary_ari_capb = boundary_ari_capa.clone();
    let boundary_arh_capc = boundary_arh_capb.clone();
    let boundary_arg_capd = boundary_arg_capc.clone();
    Rc::new(move |boundary_arl: B| -> StateExt<A, B> {
        (*{
            let boundary_arj_capb = boundary_arj_capa.clone();
            let boundary_ari_capc = boundary_ari_capb.clone();
            let boundary_arh_capd = boundary_arh_capc.clone();
            let boundary_arg_cape = boundary_arg_capd.clone();
            Rc::new(move |boundary_arka: A, boundary_arla: B| {
                (*{
                    let boundary_ari_capd = boundary_ari_capc.clone();
                    let boundary_arh_cape = boundary_arh_capd.clone();
                    let boundary_arg_capf = boundary_arg_cape.clone();
                    Rc::new(move |boundary_arja: A, boundary_arkb: A, boundary_arlb: B| {
                        (*{
                            let boundary_arh_capf = boundary_arh_cape.clone();
                            let boundary_arg_capg = boundary_arg_capf.clone();
                            Rc::new(move |boundary_aria: BigInt, boundary_arjb: A, boundary_arkc: A, boundary_arlc: B| {
                                (*{
                                    let boundary_arg_caph = boundary_arg_capg.clone();
                                    Rc::new(move |boundary_arha: BigInt, boundary_arib: BigInt, boundary_arjc: A, boundary_arkd: A, boundary_arld: B| {
                                        StateExt::StateExt (boundary_arg_caph.clone(), boundary_arha.clone(), boundary_arib.clone(), boundary_arjc.clone(), boundary_arkd.clone(), boundary_arld.clone())
                                    })
                                })(boundary_arh_capf.clone(), boundary_aria.clone(), boundary_arjb.clone(), boundary_arkc.clone(), boundary_arlc.clone())
                            })
                        })(boundary_ari_capd.clone(), boundary_arja.clone(), boundary_arkb.clone(), boundary_arlb.clone())
                    })
                })(boundary_arj_capb.clone(), boundary_arka.clone(), boundary_arla.clone())
            })
        })(boundary_ark_cap.clone(), boundary_arl.clone())
    })
}) as Rc<dyn Fn(B) -> StateExt<A, B>>)
                                    })
                                }) as Rc<dyn Fn(A) -> Rc<dyn Fn(B) -> StateExt<A,
 B>>>)
                            })
                        }) as Rc<dyn Fn(A) -> Rc<dyn Fn(A) -> Rc<dyn Fn(B) -> StateExt<A,
         B>>>>)
                    })
                }) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(A) -> Rc<dyn Fn(A) -> Rc<dyn Fn(B) -> StateExt<A,
                      B>>>>>)
            })
        }) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(BigInt) -> Rc<dyn Fn(A) -> Rc<dyn Fn(A) -> Rc<dyn Fn(B) -> StateExt<A,
                                   B>>>>>>)
    })) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(BigInt) -> Rc<dyn Fn(BigInt) -> Rc<dyn Fn(A) -> Rc<dyn Fn(A) -> Rc<dyn Fn(B) -> StateExt<A,
             B>>>>>>>),
    ((Rc::new(move |_: Unit| -> Term {
        Term::Const (Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))
    })) as Rc<dyn Fn(Unit) -> Term>)
), x_capd.clone()), y_capc.clone()), z_capb.clone()), aa_capa.clone()), ab_cap.clone()), ac.clone()))
                                    })
                                }) as Rc<dyn Fn((B, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
                                i_capd.clone()
                            )
                        })
                    }) as Rc<dyn Fn((A, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
                    i_capc.clone()
                )
            })
        }) as Rc<dyn Fn((A, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
        i_capb.clone()
    )
})
                                    }) as Rc<dyn Fn((BigInt, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
                                    i_capa.clone()
                                )
                            })
                        }) as Rc<dyn Fn((BigInt, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
                        i_cap.clone()
                    )
                })
            }) as Rc<dyn Fn((BigInt, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
            i.clone()
        )
    }
}

impl <A : Clone + Typerep + PartialTermOf + 'static, 
       B : Clone + Typerep + PartialTermOf + 'static>
    PartialTermOf for StateExt<A, B> {
    fn partial_term_of (x0: Itself<StateExt<A, B>>, x1: NarrowingTerm) -> Term {
        match x1 {
            NarrowingTerm::NarrowingVariable (_, _) =>
                Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerepa::Typerep (Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil))))))),
            NarrowingTerm::NarrowingConstructor (p0, p0a) =>
                panic!("non-exhaustive match"),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
