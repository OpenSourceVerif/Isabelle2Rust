use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::One;
use crate::Arith::Sgn;
use crate::Arith::Uminus;
use crate::Arith::Zero;
use crate::GCD::Gcda;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::filter;
use crate::List::mapa;
use crate::List::remdups_adj;
use crate::List::size_list;
use crate::Misc_Polynomial::poly_inf;
use crate::Misc_Polynomial::poly_neg_inf;
use crate::Polynomial::Poly;
use crate::Polynomial::degree;
use crate::Polynomial::div_field_poly_impl;
use crate::Polynomial::pderiv;
use crate::Polynomial::poly;
use crate::Real::Real;
use crate::Real::less_real;
use crate::Real_Vector_Spaces::RealNormedVector;
use crate::Rings::Modulo;

use std::rc::Rc;

pub fn sturm_aux (p: Poly<Real>, q: Poly<Real>) -> List<Poly<Real>> {
    if degree(q.clone()) == BigInt::ZERO {
        List::Cons (p.clone(), Box::new(List::Cons (q.clone(), Box::new(List::Nil))))
    } else {
        List::Cons (p.clone(), Box::new(sturm_aux(q.clone(), <Poly<Real> as Uminus>::uminus(<Poly<Real> as Modulo>::modulo(p.clone(), q.clone())))))
    }
}

pub fn sturm (p: Poly<Real>) -> List<Poly<Real>> {
    sturm_aux(p.clone(), pderiv(p.clone()))
}

pub fn sign_changes_neg_inf <A> (ps: List<Poly<A>>) -> BigInt
where
    A : Clone + Equal + RealNormedVector + 'static
{
    (match (size_list(remdups_adj(filter(
          ((Rc::new(move |x: A| -> bool {
              ! eq(x.clone(), <A as Zero>::zero())
          })) as Rc<dyn Fn(A) -> bool>),
          mapa(((Rc::new(move |a: Poly<A>| -> A {
              poly_neg_inf(a.clone())
          })) as Rc<dyn Fn(Poly<A>) -> A>), ps.clone())
      ))).clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
}

pub fn sign_changes_inf <A> (ps: List<Poly<A>>) -> BigInt
where
    A : Clone + Equal + RealNormedVector + 'static
{
    (match (size_list(remdups_adj(filter(
          ((Rc::new(move |x: A| -> bool {
              ! eq(x.clone(), <A as Zero>::zero())
          })) as Rc<dyn Fn(A) -> bool>),
          mapa(((Rc::new(move |a: Poly<A>| -> A {
              poly_inf(a.clone())
          })) as Rc<dyn Fn(Poly<A>) -> A>), ps.clone())
      ))).clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
}

pub fn count_roots (p: Poly<Real>) -> BigInt {
    if <Poly<Real> as Equal>::equal(p.clone(), <Poly<Real> as Zero>::zero()) {
        BigInt::ZERO
    } else {
        {
            let ps = sturm(p.clone());
            (match (sign_changes_neg_inf(ps.clone()).clone(), sign_changes_inf(ps.clone()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
        }
    }
}

pub fn sign_changes (ps: List<Poly<Real>>, x: Real) -> BigInt {
    (match (size_list(remdups_adj(filter(
          ((Rc::new(move |xa: Real| -> bool {
              ! <Real as Equal>::equal(xa.clone(), <Real as Zero>::zero())
          })) as Rc<dyn Fn(Real) -> bool>),
          mapa(
              (({
                  let x_cap = x.clone();
                  Rc::new(move |p: Poly<Real>| -> Real {
                      <Real as Sgn>::sgn(poly(p.clone(), x_cap.clone()))
                  })
              }) as Rc<dyn Fn(Poly<Real>) -> Real>),
              ps.clone()
          )
      ))).clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
}

pub fn sturm_squarefree (p: Poly<Real>) -> List<Poly<Real>> {
    sturm(div_field_poly_impl(p.clone(), <Poly<Real> as Gcda>::gcda(p.clone(), pderiv(p.clone()))))
}

pub fn count_roots_above (p: Poly<Real>, a: Real) -> BigInt {
    let q = pderiv(p.clone());
    if <Poly<Real> as Equal>::equal(p.clone(), <Poly<Real> as Zero>::zero()) {
        BigInt::ZERO
    } else {
        if ! <Real as Equal>::equal(poly(p.clone(), a.clone()), <Real as Zero>::zero()) ||
             ! <Real as Equal>::equal(poly(q.clone(), a.clone()), <Real as Zero>::zero()) {
            {
                let ps = sturm(p.clone());
                (match (sign_changes(ps.clone(), a.clone()).clone(), sign_changes_inf(ps.clone()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
            }
        } else {
            {
                let ps = sturm_squarefree(p.clone());
                (match (sign_changes(ps.clone(), a.clone()).clone(), sign_changes_inf(ps.clone()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
            }
        }
    }
}

pub fn count_roots_below (p: Poly<Real>, a: Real) -> BigInt {
    let q = pderiv(p.clone());
    if <Poly<Real> as Equal>::equal(p.clone(), <Poly<Real> as Zero>::zero()) {
        BigInt::ZERO
    } else {
        if ! <Real as Equal>::equal(poly(p.clone(), a.clone()), <Real as Zero>::zero()) ||
             ! <Real as Equal>::equal(poly(q.clone(), a.clone()), <Real as Zero>::zero()) {
            {
                let ps = sturm(p.clone());
                (match (sign_changes_neg_inf(ps.clone()).clone(), sign_changes(ps.clone(), a.clone()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
            }
        } else {
            {
                let ps = sturm_squarefree(p.clone());
                (match (sign_changes_neg_inf(ps.clone()).clone(), sign_changes(ps.clone(), a.clone()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
            }
        }
    }
}

pub fn sturm_squarefreea (p: Poly<Real>) -> List<Poly<Real>> {
    let d = <Poly<Real> as Gcda>::gcda(p.clone(), pderiv(p.clone()));
    mapa(
        (({
            let d_cap = d.clone();
            Rc::new(move |pa: Poly<Real>| -> Poly<Real> {
                div_field_poly_impl(pa.clone(), d_cap.clone())
            })
        }) as Rc<dyn Fn(Poly<Real>) -> Poly<Real>>),
        sturm(p.clone())
    )
}

pub fn split_sign_changes
    (xa0: List<Poly<Real>>, x: Real) -> List<List<Poly<Real>>> {
    match xa0 {
        List::Cons (p, p0a) =>
            match *p0a {
                List::Nil =>
                    List::Cons (List::Cons (p.clone(), Box::new(List::Nil)), Box::new(List::Nil)),
                List::Cons (q, p1a) =>
                    match *p1a {
                        List::Nil =>
                            List::Cons (List::Cons (p.clone(), Box::new(List::Cons (q.clone(), Box::new(List::Nil)))), Box::new(List::Nil)),
                        List::Cons (r, p2a) =>
                            {
                                let ps = *p2a;
                                let xa = x;
                                if ! <Real as Equal>::equal(poly(p.clone(), xa.clone()), <Real as Zero>::zero()) &&
                                     <Real as Equal>::equal(poly(q.clone(), xa.clone()), <Real as Zero>::zero()) {
                                    List::Cons (List::Cons (p.clone(), Box::new(List::Cons (q.clone(), Box::new(List::Cons (r.clone(), Box::new(List::Nil)))))), Box::new(split_sign_changes(List::Cons (r.clone(), Box::new(ps.clone())), xa.clone())))
                                } else {
                                    List::Cons (List::Cons (p.clone(), Box::new(List::Cons (q.clone(), Box::new(List::Nil)))), Box::new(split_sign_changes(List::Cons (q.clone(), Box::new(List::Cons (r.clone(), Box::new(ps.clone())))), xa.clone())))
                                }
                            },
                        _ =>
                            panic!("non-exhaustive match")
                    },
                _ =>
                    panic!("non-exhaustive match")
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn count_roots_between (p: Poly<Real>, a: Real, b: Real) -> BigInt {
    let q = pderiv(p.clone());
    if less_real(b.clone(), a.clone()) ||
         <Poly<Real> as Equal>::equal(p.clone(), <Poly<Real> as Zero>::zero()) {
        BigInt::ZERO
    } else {
        if (! <Real as Equal>::equal(poly(p.clone(), a.clone()), <Real as Zero>::zero()) ||
             ! <Real as Equal>::equal(poly(q.clone(), a.clone()), <Real as Zero>::zero())) &&
             (! <Real as Equal>::equal(poly(p.clone(), b.clone()), <Real as Zero>::zero()) ||
               ! <Real as Equal>::equal(poly(q.clone(), b.clone()), <Real as Zero>::zero())) {
            {
                let ps = sturm(p.clone());
                (match (sign_changes(ps.clone(), a.clone()).clone(), sign_changes(ps.clone(), b.clone()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
            }
        } else {
            {
                let ps = sturm_squarefree(p.clone());
                (match (sign_changes(ps.clone(), a.clone()).clone(), sign_changes(ps.clone(), b.clone()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
            }
        }
    }
}
