use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::Fun::comp;
use crate::Fun::id;
use crate::List::List;
use crate::Orderings::Ord;
use crate::Orderings::max;
use crate::Product_Type::apsnd;
use crate::Product_Type::fst;
use crate::Product_Type::snd;
use crate::Pure::Itself;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::Quickcheck_Narrowing::PartialTermOf;
use crate::String::Literal;
use crate::Typerep::Typerepa;

use std::rc::Rc;

impl crate::Typerep::Typerep for Num {
    fn typerep (x0: Itself<Self>) -> Typerepa { panic!("unimplemented instance method: typerep") }
}

#[derive(Clone)]
pub enum Num {
    One,
    Bit0 (Box<Num>),
    Bit1 (Box<Num>)
}

impl crate::Typerep::Typerep for Natural {
    fn typerep (x0: Itself<Self>) -> Typerepa { panic!("unimplemented instance method: typerep") }
}

#[derive(Clone)]
pub enum Natural {
    Nat (BigInt)
}

pub fn one_nat () -> BigInt {
    BigInt::from_bytes_be(Sign::Plus, &[1])
}

pub fn funpow <A> (n: BigInt, f: Rc<dyn Fn(A) -> A>) -> Rc<dyn Fn(A) -> A>
where
    A : Clone + 'static
{
    if n.clone() == BigInt::ZERO {
        ((Rc::new(move |a: A| -> A {
            id(a.clone())
        })) as Rc<dyn Fn(A) -> A>)
    } else {
        (({
            let n_cap = n.clone();
            let f_cap = f.clone();
            Rc::new(move |a: A| -> A {
                (*comp(f_cap.clone(), (({
                    let f_capa = f_cap.clone();
                    let n_capa = n_cap.clone();
                    Rc::new(move |aa: A| -> A {
                        (*funpow((match (n_capa.clone().clone(), one_nat().clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } }), f_capa.clone()))(aa.clone())
                    })
                }) as Rc<dyn Fn(A) -> A>)))(a.clone())
            })
        }) as Rc<dyn Fn(A) -> A>)
    }
}

pub fn plus_num (x0: Num, x1: Num) -> Num {
    match (x0, x1) {
        (Num::Bit1 (p0), Num::Bit1 (p1)) =>
            {
                let m = *p0;
                let n = *p1;
                Num::Bit0 (Box::new(plus_num(plus_num(m.clone(), n.clone()), Num::One)))
            },
        (Num::Bit1 (p0), Num::Bit0 (p1)) =>
            {
                let m = *p0;
                let n = *p1;
                Num::Bit1 (Box::new(plus_num(m.clone(), n.clone())))
            },
        (Num::Bit1 (p0), Num::One) =>
            {
                let m = *p0;
                Num::Bit0 (Box::new(plus_num(m.clone(), Num::One)))
            },
        (Num::Bit0 (p0), Num::Bit1 (p1)) =>
            {
                let m = *p0;
                let n = *p1;
                Num::Bit1 (Box::new(plus_num(m.clone(), n.clone())))
            },
        (Num::Bit0 (p0), Num::Bit0 (p1)) =>
            {
                let m = *p0;
                let n = *p1;
                Num::Bit0 (Box::new(plus_num(m.clone(), n.clone())))
            },
        (Num::Bit0 (p0), Num::One) =>
            {
                let m = *p0;
                Num::Bit1 (Box::new(m.clone()))
            },
        (Num::One, Num::Bit1 (p0)) =>
            {
                let n = *p0;
                Num::Bit0 (Box::new(plus_num(n.clone(), Num::One)))
            },
        (Num::One, Num::Bit0 (p0)) =>
            {
                let n = *p0;
                Num::Bit1 (Box::new(n.clone()))
            },
        (Num::One, Num::One) =>
            Num::Bit0 (Box::new(Num::One)),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn divmod_integer (k: BigInt, l: BigInt) -> (BigInt, BigInt) {
    if k.clone() == BigInt::ZERO {
        (BigInt::ZERO, BigInt::ZERO)
    } else {
        if BigInt::ZERO < l.clone() {
            if BigInt::ZERO < k.clone() {
                std::convert::identity::<(BigInt, BigInt)>((match (k.clone().clone(), l.clone().clone()) { (k, l) => { let k = k.abs(); let l = l.abs(); if l == BigInt::ZERO { (BigInt::ZERO, k) } else { let q = k.clone() / l.clone(); let r = k % l; (q, r) } } }))
            } else {
                match std::convert::identity::<(BigInt, BigInt)>((match (k.clone().clone(), l.clone().clone()) { (k, l) => { let k = k.abs(); let l = l.abs(); if l == BigInt::ZERO { (BigInt::ZERO, k) } else { let q = k.clone() / l.clone(); let r = k % l; (q, r) } } })) {
                    (r, s) =>
                        if s.clone() == BigInt::ZERO {
                            ((- r.clone()), BigInt::ZERO)
                        } else {
                            ((- r.clone()) -
                               BigInt::from_bytes_be(Sign::Plus, &[1]), l.clone() -
                                  s.clone())
                        },
                    _ =>
                        panic!("non-exhaustive match")
                }
            }
        } else {
            if l.clone() == BigInt::ZERO {
                (BigInt::ZERO, k.clone())
            } else {
                apsnd(
                    ((Rc::new(move |a: BigInt| -> BigInt {
                        (- a.clone())
                    })) as Rc<dyn Fn(BigInt) -> BigInt>),
                    if k.clone() < BigInt::ZERO {
                        std::convert::identity::<(BigInt, BigInt)>((match (k.clone().clone(), l.clone().clone()) { (k, l) => { let k = k.abs(); let l = l.abs(); if l == BigInt::ZERO { (BigInt::ZERO, k) } else { let q = k.clone() / l.clone(); let r = k % l; (q, r) } } }))
                    } else {
                        match std::convert::identity::<(BigInt, BigInt)>((match (k.clone().clone(), l.clone().clone()) { (k, l) => { let k = k.abs(); let l = l.abs(); if l == BigInt::ZERO { (BigInt::ZERO, k) } else { let q = k.clone() / l.clone(); let r = k % l; (q, r) } } })) {
                            (r, s) =>
                                if s.clone() == BigInt::ZERO {
                                    ((- r.clone()), BigInt::ZERO)
                                } else {
                                    ((- r.clone()) -
                                       BigInt::from_bytes_be(Sign::Plus, &[1]), (- l.clone()) -
  s.clone())
                                },
                            _ =>
                                panic!("non-exhaustive match")
                        }
                    }
                )
            }
        }
    }
}

pub fn num_of_integer (k: BigInt) -> Num {
    if k.clone() <= BigInt::from_bytes_be(Sign::Plus, &[1]) {
        Num::One
    } else {
        match divmod_integer(k.clone(), BigInt::from_bytes_be(Sign::Plus, &[2])) {
            (l, j) =>
                {
                    let la = num_of_integer(l.clone());
                    let lb = plus_num(la.clone(), la.clone());
                    if j.clone() == BigInt::ZERO {
                        lb.clone()
                    } else {
                        plus_num(lb.clone(), Num::One)
                    }
                },
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

pub fn integer_of_natural (x0: Natural) -> BigInt {
    let Natural::Nat (x) = x0;
    x.clone()
}

pub fn natural_of_integer (k: BigInt) -> Natural {
    Natural::Nat (max(BigInt::ZERO, k.clone()))
}

impl TermOf for Num {
    fn term_of (x0: Num) -> Term {
        match x0 {
            Num::One =>
                Term::Const (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, true, true, false, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil))),
            Num::Bit0 (p0) =>
                {
                    let a = *p0;
                    Term::App (Box::new(Term::Const (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, false, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))))))), Box::new(<Num as TermOf>::term_of(a.clone())))
                },
            Num::Bit1 (p0) =>
                {
                    let a = *p0;
                    Term::App (Box::new(Term::Const (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, true, true, false, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))))))), Box::new(<Num as TermOf>::term_of(a.clone())))
                },
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl TermOf for BigInt {
    fn term_of (i: BigInt) -> Term {
        if BigInt::ZERO < i.clone() {
            Term::App (Box::new(Term::Const (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))))))), Box::new(<Num as TermOf>::term_of(num_of_integer(i.clone()))))
        } else {
            if i.clone() == BigInt::ZERO {
                Term::Const (Literal::Literal (true, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, true, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, true, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)))
            } else {
                Term::App (Box::new(Term::Const (Literal::Literal (true, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))))))), Box::new(<BigInt as TermOf>::term_of((- i.clone()))))
            }
        }
    }
}

pub fn nat_of_natural (x: Natural) -> BigInt {
    (*comp(((Rc::new(move |a: BigInt| -> BigInt {
        (match a.clone().clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })
    })) as Rc<dyn Fn(BigInt) -> BigInt>), ((Rc::new(move |a: Natural| -> BigInt {
        integer_of_natural(a.clone())
    })) as Rc<dyn Fn(Natural) -> BigInt>)))(x.clone())
}

pub fn one_natural () -> Natural {
    Natural::Nat (BigInt::from_bytes_be(Sign::Plus, &[1]))
}

pub fn plus_natural (m: Natural, n: Natural) -> Natural {
    Natural::Nat (integer_of_natural(m.clone()) + integer_of_natural(n.clone()))
}

pub fn zero_natural () -> Natural {
    Natural::Nat (BigInt::ZERO)
}

impl crate::HOL::Equal for Natural {
    fn equal (m: Natural, n: Natural) -> bool {
        integer_of_natural(m.clone()) == integer_of_natural(n.clone())
    }
}

pub fn minus_natural (m: Natural, n: Natural) -> Natural {
    Natural::Nat (max(BigInt::ZERO, integer_of_natural(m.clone()) -
                                      integer_of_natural(n.clone())))
}

impl Ord for Natural {
    fn less_eq (m: Natural, n: Natural) -> bool {
        integer_of_natural(m.clone()) <= integer_of_natural(n.clone())
    }
    fn less (m: Natural, n: Natural) -> bool {
        integer_of_natural(m.clone()) < integer_of_natural(n.clone())
    }
}

pub fn times_natural (m: Natural, n: Natural) -> Natural {
    Natural::Nat (integer_of_natural(m.clone()) * integer_of_natural(n.clone()))
}

pub fn divide_integer (k: BigInt, l: BigInt) -> BigInt {
    fst(divmod_integer(k.clone(), l.clone()))
}

pub fn divide_natural (m: Natural, n: Natural) -> Natural {
    Natural::Nat (divide_integer(integer_of_natural(m.clone()), integer_of_natural(n.clone())))
}

pub fn modulo_integer (k: BigInt, l: BigInt) -> BigInt {
    snd(divmod_integer(k.clone(), l.clone()))
}

pub fn modulo_natural (m: Natural, n: Natural) -> Natural {
    Natural::Nat (modulo_integer(integer_of_natural(m.clone()), integer_of_natural(n.clone())))
}

impl PartialTermOf for BigInt {
    fn partial_term_of (x0: Itself<BigInt>, x1: NarrowingTerm) -> Term {
        match x1 {
            NarrowingTerm::NarrowingVariable (_, _) =>
                Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil))),
            NarrowingTerm::NarrowingConstructor (p0, p0a) =>
                panic!("non-exhaustive match"),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl TermOf for Natural {
    fn term_of (x: Natural) -> Term {
        Term::App (Box::new(Term::Const (Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))))))), Box::new(<BigInt as TermOf>::term_of(integer_of_natural(x.clone()))))
    }
}
