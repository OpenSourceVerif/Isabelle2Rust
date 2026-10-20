use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Natural;
use crate::Arith::Num;
use crate::Arith::divide_natural;
use crate::Arith::minus_natural;
use crate::Arith::modulo_natural;
use crate::Arith::natural_of_integer;
use crate::Arith::one_natural;
use crate::Arith::plus_natural;
use crate::Arith::times_natural;
use crate::Arith::zero_natural;
use crate::HOL::Equal;
use crate::Orderings::Ord;
use crate::Product_Type::scomp;

use std::rc::Rc;

pub fn log (b: Natural, i: Natural) -> Natural {
    if <Natural as Ord>::less_eq(b.clone(), one_natural()) ||
         <Natural as Ord>::less(i.clone(), b.clone()) {
        one_natural()
    } else {
        plus_natural(one_natural(), log(b.clone(), divide_natural(i.clone(), b.clone())))
    }
}

pub fn minus_shift (r: Natural, k: Natural, l: Natural) -> Natural {
    if <Natural as Ord>::less(k.clone(), l.clone()) {
        minus_natural(plus_natural(r.clone(), k.clone()), l.clone())
    } else {
        minus_natural(k.clone(), l.clone())
    }
}

pub fn next (x0: (Natural, Natural)) -> (Natural, (Natural, Natural)) {
    match x0 {
        (v, w) =>
            {
                let k = divide_natural(v.clone(), natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[209, 164])));
                let va = minus_shift(natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[127, 255, 255, 171])), times_natural(modulo_natural(v.clone(), natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[209, 164]))), natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[156, 78]))), times_natural(k.clone(), natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[47, 179]))));
                let l = divide_natural(w.clone(), natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[206, 38])));
                let wa = minus_shift(natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[127, 255, 255, 7])), times_natural(modulo_natural(w.clone(), natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[206, 38]))), natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[158, 244]))), times_natural(l.clone(), natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[14, 207]))));
                let z = plus_natural(minus_shift(natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[127, 255, 255, 170])), va.clone(), plus_natural(wa.clone(), one_natural())), one_natural());
                (z.clone(), (va.clone(), wa.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn iterate <B, A>
    (k: Natural, f: Rc<dyn Fn(A, B) -> (A, B)>, x: A) -> Rc<dyn Fn(B) -> (A, B)>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    if <Natural as Equal>::equal(k.clone(), zero_natural()) {
        (({
            let x_cap = x.clone();
            Rc::new(move |a: B| -> (A, B) {
                (x_cap.clone(), a.clone())
            })
        }) as Rc<dyn Fn(B) -> (A, B)>)
    } else {
        (({
            let k_cap = k.clone();
            let x_cap = x.clone();
            let f_cap = f.clone();
            Rc::new(move |a: B| -> (A, B) {
                (*scomp((({
                    let x_capa = x_cap.clone();
                    let f_capa = f_cap.clone();
                    Rc::new(move |b: B| -> (A, B) {
                        (*f_capa)(x_capa.clone(), b.clone())
                    })
                }) as Rc<dyn Fn(B) -> (A, B)>), (({
                    let f_capa = f_cap.clone();
                    let k_capa = k_cap.clone();
                    Rc::new(move |aa: A, b: B| -> (A, B) {
                        (*iterate(minus_natural(k_capa.clone(), one_natural()), f_capa.clone(), aa.clone()))(b.clone())
                    })
                }) as Rc<dyn Fn(A, B) -> (A, B)>)))(a.clone())
            })
        }) as Rc<dyn Fn(B) -> (A, B)>)
    }
}

pub fn rangea
    (k: Natural) -> Rc<dyn Fn((Natural, Natural)) -> (Natural, (Natural, Natural))> {
    (({
        let k_cap = k.clone();
        Rc::new(move |a: (Natural, Natural)| -> (Natural, (Natural, Natural)) {
            (*scomp(
                (({
                    let k_capa = k_cap.clone();
                    Rc::new(move |aa: (Natural, Natural)| -> (Natural, (Natural, Natural)) {
                        (*iterate(
                            log(natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[127, 255, 255, 169])), k_capa.clone()),
                            ((Rc::new(move |l: Natural, eta_arg: (Natural, Natural)| -> (Natural, (Natural, Natural)) {
                                (*scomp(
                                    ((Rc::new(move |ab: (Natural, Natural)| -> (Natural, (Natural, Natural)) {
                                        next(ab.clone())
                                    })) as Rc<dyn Fn((Natural, Natural)) -> (Natural, (Natural, Natural))>),
                                    (({
                                        let l_cap = l.clone();
Rc::new(move |v: Natural, eta_arh: (Natural, Natural)| -> (Natural, (Natural, Natural)) {
    (plus_natural(v.clone(), times_natural(l_cap.clone(), natural_of_integer(BigInt::from_bytes_be(Sign::Plus, &[127, 255, 255, 169])))), eta_arh.clone())
})
                                    }) as Rc<dyn Fn(Natural,
             (Natural, Natural)) -> (Natural, (Natural, Natural))>)
                                ))(eta_arg.clone())
                            })) as Rc<dyn Fn(Natural,
      (Natural, Natural)) -> (Natural, (Natural, Natural))>),
                            one_natural()
                        ))(aa.clone())
                    })
                }) as Rc<dyn Fn((Natural, Natural)) -> (Natural, (Natural, Natural))>),
                (({
                    let k_capa = k_cap.clone();
                    Rc::new(move |v: Natural, eta_arg: (Natural, Natural)| -> (Natural, (Natural, Natural)) {
                        (modulo_natural(v.clone(), k_capa.clone()), eta_arg.clone())
                    })
                }) as Rc<dyn Fn(Natural,
                                 (Natural, Natural)) -> (Natural, (Natural, Natural))>)
            ))(a.clone())
        })
    }) as Rc<dyn Fn((Natural, Natural)) -> (Natural, (Natural, Natural))>)
}
