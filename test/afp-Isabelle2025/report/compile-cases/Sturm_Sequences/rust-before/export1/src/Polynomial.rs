use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::AbGroupAdd;
use crate::Arith::CommMonoidAdd;
use crate::Arith::GroupAdd;
use crate::Arith::Minus;
use crate::Arith::One;
use crate::Arith::Plus;
use crate::Arith::Times;
use crate::Arith::Uminus;
use crate::Arith::Zero;
use crate::Fields::Field;
use crate::Fields::Inverse;
use crate::Fun::id;
use crate::GCD::Gcda;
use crate::GCD::SemiringGcda;
use crate::Groups_List::horner_sum;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::foldr;
use crate::List::hd;
use crate::List::last;
use crate::List::mapa;
use crate::List::null;
use crate::List::rev;
use crate::List::size_list;
use crate::List::tl;
use crate::More_List::nth_default;
use crate::More_List::strip_while;
use crate::Product_Type::fst;
use crate::Rings::CommRing1;
use crate::Rings::CommSemiring0;
use crate::Rings::CommSemiring1;
use crate::Rings::Divide;
use crate::Rings::IdomDivide;
use crate::Rings::SemidomDivideUnitFactor;
use crate::Rings::Semiring1NoZeroDivisors;
use crate::Rings::SemiringNoZeroDivisors;
use crate::Rings::UnitFactor;

use std::rc::Rc;

impl <A : Clone + Zero + Equal + IdomDivide + SemidomDivideUnitFactor + 'static>
    UnitFactor for Poly<A> {
    fn unit_factor (x0: Self) -> Self { panic!("unimplemented instance method: unit_factor") }
}

impl <A : Clone + Zero + Equal + IdomDivide + SemidomDivideUnitFactor + 'static>
    Minus for Poly<A> {
    fn minus (x0: Self,
              x1: Self) -> Self { panic!("unimplemented instance method: minus") }
}

impl <A : Clone + Zero + Equal + IdomDivide + SemidomDivideUnitFactor + 'static>
    Plus for Poly<A> {
    fn plus (x0: Self,
             x1: Self) -> Self { panic!("unimplemented instance method: plus") }
}

impl <A : Clone + Zero + Equal + IdomDivide + SemidomDivideUnitFactor + 'static>
    Times for Poly<A> {
    fn times (x0: Self,
              x1: Self) -> Self { panic!("unimplemented instance method: times") }
}

impl <A : Clone + Zero + Equal + IdomDivide + SemidomDivideUnitFactor + 'static>
    One for Poly<A> {
    fn one () -> Self { panic!("unimplemented instance method: one") }
}

#[derive(Clone)]
pub enum Poly<A> {
    Poly (List<A>)
}

pub fn coeffs <A> (x0: Poly<A>) -> List<A>
where
    A : Clone + Zero + 'static
{
    let Poly::Poly (x) = x0;
    x.clone()
}

pub fn poly <A> (p: Poly<A>, a: A) -> A
where
    A : Clone + CommSemiring0 + 'static
{
    horner_sum(((Rc::new(move |aa: A| -> A {
        id(aa.clone())
    })) as Rc<dyn Fn(A) -> A>), a.clone(), coeffs(p.clone()))
}

pub fn c_cons <A> (x: A, xs: List<A>) -> List<A>
where
    A : Clone + Zero + Equal + 'static
{
    if null(xs.clone()) && eq(x.clone(), <A as Zero>::zero()) {
        List::Nil
    } else {
        List::Cons (x.clone(), Box::new(xs.clone()))
    }
}

pub fn p_cons <A> (a: A, p: Poly<A>) -> Poly<A>
where
    A : Clone + Zero + Equal + 'static
{
    Poly::Poly (c_cons(a.clone(), coeffs(p.clone())))
}

pub fn smult <A> (a: A, p: Poly<A>) -> Poly<A>
where
    A : Clone + Equal + CommSemiring0 + SemiringNoZeroDivisors + 'static
{
    Poly::Poly (
        if eq(a.clone(), <A as Zero>::zero()) {
            List::Nil
        } else {
            mapa((({
                let a_cap = a.clone();
                Rc::new(move |b: A| -> A {
                    <A as Times>::times(a_cap.clone(), b.clone())
                })
            }) as Rc<dyn Fn(A) -> A>), coeffs(p.clone()))
        }
    )
}

pub fn degree <A> (p: Poly<A>) -> BigInt
where
    A : Clone + Zero + 'static
{
    (match (size_list(coeffs(p.clone())).clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })
}

pub fn pderiv_coeffs_code <A> (f: A, x1: List<A>) -> List<A>
where
    A : Clone + Equal + CommSemiring1 + SemiringNoZeroDivisors + 'static
{
    match (f, x1) {
        (f, List::Cons (x, p0)) =>
            {
                let xs = *p0;
                c_cons(<A as Times>::times(f.clone(), x.clone()), pderiv_coeffs_code(<A as Plus>::plus(f.clone(), <A as One>::one()), xs.clone()))
            },
        (_, List::Nil) =>
            List::Nil,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn pderiv_coeffs <A> (xs: List<A>) -> List<A>
where
    A : Clone + Equal + CommSemiring1 + SemiringNoZeroDivisors + 'static
{
    pderiv_coeffs_code(<A as One>::one(), tl(xs.clone()))
}

pub fn pderiv <A> (p: Poly<A>) -> Poly<A>
where
    A : Clone + Equal + CommSemiring1 + SemiringNoZeroDivisors + 'static
{
    Poly::Poly (pderiv_coeffs(coeffs(p.clone())))
}

pub fn fold_coeffs <B, A>
    (f: Rc<dyn Fn(A, B) -> B>, p: Poly<A>) -> Rc<dyn Fn(B) -> B>
where
    A : Clone + Zero + 'static,
    B : Clone + 'static
{
    (({
        let p_cap = p.clone();
        let f_cap = f.clone();
        Rc::new(move |a: B| -> B {
            (*foldr(f_cap.clone(), coeffs(p_cap.clone())))(a.clone())
        })
    }) as Rc<dyn Fn(B) -> B>)
}

pub fn content <A> (p: Poly<A>) -> A
where
    A : Clone + SemiringGcda + 'static
{
    (*fold_coeffs(((Rc::new(move |a: A, b: A| -> A {
        <A as Gcda>::gcda(a.clone(), b.clone())
    })) as Rc<dyn Fn(A, A) -> A>), p.clone()))(<A as Zero>::zero())
}

pub fn is_zero <A> (p: Poly<A>) -> bool
where
    A : Clone + Zero + 'static
{
    null(coeffs(p.clone()))
}

pub fn map_poly <A, B> (f: Rc<dyn Fn(B) -> A>, p: Poly<B>) -> Poly<A>
where
    B : Clone + Zero + 'static,
    A : Clone + Zero + Equal + 'static
{
    Poly::Poly ((*strip_while(((Rc::new(move |a: A| -> bool {
        eq(<A as Zero>::zero(), a.clone())
    })) as Rc<dyn Fn(A) -> bool>)))(mapa(f.clone(), coeffs(p.clone()))))
}

pub fn coeff <A> (p: Poly<A>) -> Rc<dyn Fn(BigInt) -> A>
where
    A : Clone + Zero + 'static
{
    (({
        let p_cap = p.clone();
        Rc::new(move |a: BigInt| -> A {
            nth_default(<A as Zero>::zero(), coeffs(p_cap.clone()), a.clone())
        })
    }) as Rc<dyn Fn(BigInt) -> A>)
}

pub fn minus_poly_rev_list <A> (xs: List<A>, x1: List<A>) -> List<A>
where
    A : Clone + GroupAdd + 'static
{
    match (xs, x1) {
        (List::Cons (x, p0), List::Cons (y, p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                List::Cons (<A as Minus>::minus(x.clone(), y.clone()), Box::new(minus_poly_rev_list(xs.clone(), ys.clone())))
            },
        (xs, List::Nil) =>
            xs.clone(),
        (List::Nil, List::Cons (_, _)) =>
            List::Nil,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn pseudo_mod_main_list <A>
    (lc: A, r: List<A>, d: List<A>, n: BigInt) -> List<A>
where
    A : Clone + Equal + CommRing1 + 'static
{
    if n.clone() == BigInt::ZERO {
        r.clone()
    } else {
        {
            let rr = mapa((({
                let lc_cap = lc.clone();
                Rc::new(move |a: A| -> A {
                    <A as Times>::times(lc_cap.clone(), a.clone())
                })
            }) as Rc<dyn Fn(A) -> A>), r.clone());
            let a = hd(r.clone());
            let rrr = tl(
                if eq(a.clone(), <A as Zero>::zero()) {
                    rr.clone()
                } else {
                    minus_poly_rev_list(rr.clone(), mapa((({
                        let a_cap = a.clone();
                        Rc::new(move |b: A| -> A {
                            <A as Times>::times(a_cap.clone(), b.clone())
                        })
                    }) as Rc<dyn Fn(A) -> A>), d.clone()))
                }
            );
            pseudo_mod_main_list(lc.clone(), rrr.clone(), d.clone(), (match (n.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }))
        }
    }
}

pub fn pseudo_mod_list <A> (p: List<A>, q: List<A>) -> List<A>
where
    A : Clone + Equal + CommRing1 + 'static
{
    if null(q.clone()) {
        p.clone()
    } else {
        {
            let rq = rev(q.clone());
            let a = pseudo_mod_main_list(hd(rq.clone()), rev(p.clone()), rq.clone(), (match ((<BigInt as One>::one() +
               size_list(p.clone())).clone(), size_list(q.clone()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }));
            rev(a.clone())
        }
    }
}

pub fn poly_of_list <A> (asa: List<A>) -> Poly<A>
where
    A : Clone + CommMonoidAdd + Equal + 'static
{
    Poly::Poly ((*strip_while(((Rc::new(move |a: A| -> bool {
        eq(<A as Zero>::zero(), a.clone())
    })) as Rc<dyn Fn(A) -> bool>)))(asa.clone()))
}

pub fn pseudo_mod <A> (f: Poly<A>, g: Poly<A>) -> Poly<A>
where
    A : Clone + Equal + CommRing1 + Semiring1NoZeroDivisors + 'static
{
    poly_of_list(pseudo_mod_list(coeffs(f.clone()), coeffs(g.clone())))
}

pub fn primitive_part <A> (p: Poly<A>) -> Poly<A>
where
    A : Clone + SemiringGcda + Equal + 'static
{
    map_poly(
        (({
            let p_cap = p.clone();
            Rc::new(move |x: A| -> A {
                <A as Divide>::divide(x.clone(), content(p_cap.clone()))
            })
        }) as Rc<dyn Fn(A) -> A>),
        p.clone()
    )
}

pub fn divide_poly_main_list <A>
    (lc: A, q: List<A>, r: List<A>, d: List<A>, n: BigInt) -> List<A>
where
    A : Clone + Equal + IdomDivide + 'static
{
    if n.clone() == BigInt::ZERO {
        q.clone()
    } else {
        {
            let cr = hd(r.clone());
            if eq(cr.clone(), <A as Zero>::zero()) {
                divide_poly_main_list(lc.clone(), c_cons(cr.clone(), q.clone()), tl(r.clone()), d.clone(), (match (n.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }))
            } else {
                {
                    let a = <A as Divide>::divide(cr.clone(), lc.clone());
                    let qq = c_cons(a.clone(), q.clone());
                    let rr = minus_poly_rev_list(r.clone(), mapa((({
                        let a_cap = a.clone();
                        Rc::new(move |b: A| -> A {
                            <A as Times>::times(a_cap.clone(), b.clone())
                        })
                    }) as Rc<dyn Fn(A) -> A>), d.clone()));
                    if eq(hd(rr.clone()), <A as Zero>::zero()) {
                        divide_poly_main_list(lc.clone(), qq.clone(), tl(rr.clone()), d.clone(), (match (n.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }))
                    } else {
                        List::Nil
                    }
                }
            }
        }
    }
}

pub fn divide_poly_list <A> (f: Poly<A>, g: Poly<A>) -> Poly<A>
where
    A : Clone + Equal + IdomDivide + 'static
{
    let cg = coeffs(g.clone());
    if null(cg.clone()) {
        g.clone()
    } else {
        {
            let cf = coeffs(f.clone());
            let cgr = rev(cg.clone());
            poly_of_list(divide_poly_main_list(hd(cgr.clone()), List::Nil, rev(cf.clone()), cgr.clone(), (match ((<BigInt as One>::one() +
                                   size_list(cf.clone())).clone(), size_list(cg.clone()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })))
        }
    }
}

pub fn divmod_poly_one_main_list <A>
    (q: List<A>, r: List<A>, d: List<A>, n: BigInt) -> (List<A>, List<A>)
where
    A : Clone + Equal + CommRing1 + 'static
{
    if n.clone() == BigInt::ZERO {
        (q.clone(), r.clone())
    } else {
        {
            let a = hd(r.clone());
            let qqq = c_cons(a.clone(), q.clone());
            let rr = tl(
                if eq(a.clone(), <A as Zero>::zero()) {
                    r.clone()
                } else {
                    minus_poly_rev_list(r.clone(), mapa((({
                        let a_cap = a.clone();
                        Rc::new(move |b: A| -> A {
                            <A as Times>::times(a_cap.clone(), b.clone())
                        })
                    }) as Rc<dyn Fn(A) -> A>), d.clone()))
                }
            );
            divmod_poly_one_main_list(qqq.clone(), rr.clone(), d.clone(), (match (n.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }))
        }
    }
}

impl <A : Clone + Zero + 'static> Zero for Poly<A> {
    fn zero () -> Poly<A> {
        Poly::Poly (List::Nil)
    }
}

pub fn div_field_poly_impl <A> (f: Poly<A>, g: Poly<A>) -> Poly<A>
where
    A : Clone + Zero + Field + Equal + 'static
{
    let cg = coeffs(g.clone());
    if null(cg.clone()) {
        <Poly<A> as Zero>::zero()
    } else {
        {
            let cf = coeffs(f.clone());
            let ilc = <A as Inverse>::inverse(last(cg.clone()));
            let ch = mapa((({
                let ilc_cap = ilc.clone();
                Rc::new(move |a: A| -> A {
                    <A as Times>::times(ilc_cap.clone(), a.clone())
                })
            }) as Rc<dyn Fn(A) -> A>), cg.clone());
            let q = fst(divmod_poly_one_main_list(List::Nil, rev(cf.clone()), rev(ch.clone()), (match ((<BigInt as One>::one() +
                         size_list(cf.clone())).clone(), size_list(cg.clone()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })));
            poly_of_list(mapa((({
                let ilc_cap = ilc.clone();
                Rc::new(move |a: A| -> A {
                    <A as Times>::times(ilc_cap.clone(), a.clone())
                })
            }) as Rc<dyn Fn(A) -> A>), q.clone()))
        }
    }
}

pub fn mod_poly_one_main_list <A> (r: List<A>, d: List<A>, n: BigInt) -> List<A>
where
    A : Clone + Equal + CommRing1 + 'static
{
    if n.clone() == BigInt::ZERO {
        r.clone()
    } else {
        {
            let a = hd(r.clone());
            let rr = tl(
                if eq(a.clone(), <A as Zero>::zero()) {
                    r.clone()
                } else {
                    minus_poly_rev_list(r.clone(), mapa((({
                        let a_cap = a.clone();
                        Rc::new(move |b: A| -> A {
                            <A as Times>::times(a_cap.clone(), b.clone())
                        })
                    }) as Rc<dyn Fn(A) -> A>), d.clone()))
                }
            );
            mod_poly_one_main_list(rr.clone(), d.clone(), (match (n.clone().clone(), <BigInt as One>::one().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }))
        }
    }
}

impl <A : Clone + Zero + Equal + 'static> Equal for Poly<A> {
    fn equal (p: Poly<A>, q: Poly<A>) -> bool {
        <List<A> as Equal>::equal(coeffs(p.clone()), coeffs(q.clone()))
    }
}

impl <A : Clone + Equal + IdomDivide + 'static> Divide for Poly<A> {
    fn divide (f: Poly<A>, g: Poly<A>) -> Poly<A> {
        divide_poly_list(f.clone(), g.clone())
    }
}

impl <A : Clone + IdomDivide + Field + Equal + 'static> crate::Rings::Modulo for
    Poly<A> {
    fn modulo (f: Poly<A>, g: Poly<A>) -> Poly<A> {
        let cg = coeffs(g.clone());
        if null(cg.clone()) {
            f.clone()
        } else {
            {
                let cf = coeffs(f.clone());
                let ilc = <A as Inverse>::inverse(last(cg.clone()));
                let ch = mapa((({
                    let ilc_cap = ilc.clone();
                    Rc::new(move |a: A| -> A {
                        <A as Times>::times(ilc_cap.clone(), a.clone())
                    })
                }) as Rc<dyn Fn(A) -> A>), cg.clone());
                let r = mod_poly_one_main_list(rev(cf.clone()), rev(ch.clone()), (match ((<BigInt as One>::one() +
           size_list(cf.clone())).clone(), size_list(cg.clone()).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }));
                poly_of_list(rev(r.clone()))
            }
        }
    }
}

impl <A : Clone + AbGroupAdd + 'static> Uminus for Poly<A> {
    fn uminus (p: Poly<A>) -> Poly<A> {
        Poly::Poly (mapa(((Rc::new(move |a: A| -> A {
            <A as Uminus>::uminus(a.clone())
        })) as Rc<dyn Fn(A) -> A>), coeffs(p.clone())))
    }
}

impl <A : Clone + Zero + Equal + IdomDivide + SemidomDivideUnitFactor + 'static>
    crate::Rings::NormalizationSemidom for Poly<A> {
    fn normalize (p: Poly<A>) -> Poly<A> {
        <Poly<A> as Divide>::divide(p.clone(), p_cons(<A as UnitFactor>::unit_factor((*coeff(p.clone()))(degree(p.clone()))), <Poly<A> as Zero>::zero()))
    }
}
