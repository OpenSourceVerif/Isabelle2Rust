use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Natural;
use crate::Arith::Zero;
use crate::Arith::one_natural;
use crate::Code_Evaluation::Term;
use crate::Enum::Enum;
use crate::Finite_Set::Finite;
use crate::Fun::bij_betw;
use crate::Fun::inj_on;
use crate::HOL::all;
use crate::HOL::ex;
use crate::List::List;
use crate::List::upt;
use crate::Option::Option;
use crate::Orderings::Ord;
use crate::Product_Type::Unit;
use crate::Product_Type::product;
use crate::Pure::Itself;
use crate::Quickcheck_Narrowing::NarrowingCons;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::Quickcheck_Narrowing::cons;
use crate::Quickcheck_Narrowing::sum;
use crate::Quickcheck_Random::collapse;
use crate::Random::select_weight;
use crate::Set::Set;
use crate::Set::ball;
use crate::String::Literal;
use crate::Typerep::Typerep;

use std::rc::Rc;

#[derive(Clone)]
pub enum LatinType {
    Row,
    Col,
    Num
}

impl Enum for LatinType {
    fn enum_all (p: Rc<dyn Fn(LatinType) -> bool>) -> bool {
        (*p)(LatinType::Row) && ((*p)(LatinType::Col) && (*p)(LatinType::Num))
    }
    fn enum_ex (p: Rc<dyn Fn(LatinType) -> bool>) -> bool {
        ex(p.clone())
    }
    fn enuma () -> List<LatinType> {
        List::Cons (LatinType::Row, Box::new(List::Cons (LatinType::Col, Box::new(List::Cons (LatinType::Num, Box::new(List::Nil))))))
    }
}

#[derive(Clone)]
pub struct LatinTypeIITNLatinType ;

pub fn next (t: LatinType) -> LatinType {
    match t.clone() {
        LatinType::Row =>
            LatinType::Col,
        LatinType::Col =>
            LatinType::Num,
        LatinType::Num =>
            LatinType::Row,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn without
    (t: LatinType) -> Rc<dyn Fn(Rc<dyn Fn(LatinType) -> BigInt>) -> (BigInt, BigInt)> {
    let t_cap = t.clone();
    Rc::new(move |e: Rc<dyn Fn(LatinType) -> BigInt>| -> (BigInt, BigInt) {
        ((*e)(next(t_cap.clone())), (*e)(next(next(t_cap.clone()))))
    })
}

pub fn partial_latin_square
    (s: Set<Rc<dyn Fn(LatinType) -> BigInt>>, n: BigInt) -> bool {
    all(
          (({
              let s_cap = s.clone();
              Rc::new(move |t: LatinType| -> bool {
                  inj_on((({
                      let t_cap = t.clone();
                      Rc::new(move |a: Rc<dyn Fn(LatinType) -> BigInt>| -> (BigInt, BigInt) {
                          (*without(t_cap.clone()))(a.clone())
                      })
                  }) as Rc<dyn Fn(Rc<dyn Fn(LatinType) -> BigInt>) -> (BigInt, BigInt)>), s_cap.clone())
              })
          }) as Rc<dyn Fn(LatinType) -> bool>)
      ) &&
      ball(
          s.clone(),
          (({
              let n_cap = n.clone();
              Rc::new(move |e: Rc<dyn Fn(LatinType) -> BigInt>| -> bool {
                  all(
                      (({
                          let n_capa = n_cap.clone();
                          let e_cap = e.clone();
                          Rc::new(move |t: LatinType| -> bool {
                              (*e_cap)(t.clone()) < n_capa.clone()
                          })
                      }) as Rc<dyn Fn(LatinType) -> bool>)
                  )
              })
          }) as Rc<dyn Fn(Rc<dyn Fn(LatinType) -> BigInt>) -> bool>)
      )
}

pub fn latin_rect
    (s: Set<Rc<dyn Fn(LatinType) -> BigInt>>, m: BigInt, n: BigInt) -> bool {
    m.clone() <= n.clone() &&
      (partial_latin_square(s.clone(), n.clone()) &&
        (bij_betw(((Rc::new(move |a: Rc<dyn Fn(LatinType) -> BigInt>| -> (BigInt, BigInt) {
              (*without(LatinType::Num))(a.clone())
          })) as Rc<dyn Fn(Rc<dyn Fn(LatinType) -> BigInt>) -> (BigInt, BigInt)>), s.clone(), product(Set::Set (upt(BigInt::ZERO, m.clone())), Set::Set (upt(BigInt::ZERO, n.clone())))) &&
          bij_betw(((Rc::new(move |a: Rc<dyn Fn(LatinType) -> BigInt>| -> (BigInt, BigInt) {
              (*without(LatinType::Col))(a.clone())
          })) as Rc<dyn Fn(Rc<dyn Fn(LatinType) -> BigInt>) -> (BigInt, BigInt)>), s.clone(), product(Set::Set (upt(BigInt::ZERO, n.clone())), Set::Set (upt(BigInt::ZERO, m.clone()))))))
}

pub fn latin_square
    (s: Set<Rc<dyn Fn(LatinType) -> BigInt>>, n: BigInt) -> bool {
    all(
        (({
            let n_cap = n.clone();
            let s_cap = s.clone();
            Rc::new(move |t: LatinType| -> bool {
                bij_betw((({
                    let t_cap = t.clone();
                    Rc::new(move |a: Rc<dyn Fn(LatinType) -> BigInt>| -> (BigInt, BigInt) {
                        (*without(t_cap.clone()))(a.clone())
                    })
                }) as Rc<dyn Fn(Rc<dyn Fn(LatinType) -> BigInt>) -> (BigInt, BigInt)>), s_cap.clone(), product(Set::Set (upt(BigInt::ZERO, n_cap.clone())), Set::Set (upt(BigInt::ZERO, n_cap.clone()))))
            })
        }) as Rc<dyn Fn(LatinType) -> bool>)
    )
}

pub fn random_aux_latin_type
    (x0: Natural, x1: Natural,
      s: (Natural, Natural)) -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
    (*collapse(((Rc::new(move |a: (Natural, Natural)| -> (Rc<dyn Fn((Natural, Natural)) -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>, (Natural, Natural)) {
        (*select_weight(List::Cons ((one_natural(), ((Rc::new(move |aa: (Natural, Natural)| -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
            ((
                LatinType::Row,
                ((Rc::new(move |_: Unit| -> Term {
                    Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)))
                })) as Rc<dyn Fn(Unit) -> Term>)
            ), aa.clone())
        })) as Rc<dyn Fn((Natural, Natural)) -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)), Box::new(List::Cons ((one_natural(), ((Rc::new(move |aa: (Natural, Natural)| -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                                      ((
                                          LatinType::Col,
  ((Rc::new(move |_: Unit| -> Term {
      Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)))
  })) as Rc<dyn Fn(Unit) -> Term>)
                                      ), aa.clone())
                                  })) as Rc<dyn Fn((Natural, Natural)) -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)), Box::new(List::Cons ((one_natural(), ((Rc::new(move |aa: (Natural, Natural)| -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                        ((
                            LatinType::Num,
                            ((Rc::new(move |_: Unit| -> Term {
                                Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)))
                            })) as Rc<dyn Fn(Unit) -> Term>)
                        ), aa.clone())
                    })) as Rc<dyn Fn((Natural, Natural)) -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)), Box::new(List::Nil))))))))(a.clone())
    })) as Rc<dyn Fn((Natural, Natural)) -> (Rc<dyn Fn((Natural, Natural)) -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>, (Natural, Natural))>)))(s.clone())
}

pub fn rec_latin_type <A> (f1: A, f2: A, f3: A, x3: LatinType) -> A
where
    A : Clone + 'static
{
    match (f1, f2, f3, x3) {
        (f1, _, _, LatinType::Row) =>
            f1.clone(),
        (_, f2, _, LatinType::Col) =>
            f2.clone(),
        (_, _, f3, LatinType::Num) =>
            f3.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_latin_type (x0: LatinType) -> BigInt {
    match x0 {
        LatinType::Row =>
            BigInt::ZERO,
        LatinType::Col =>
            BigInt::ZERO,
        LatinType::Num =>
            BigInt::ZERO,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_latin_typea (x0: LatinType) -> BigInt {
    match x0 {
        LatinType::Row =>
            BigInt::ZERO,
        LatinType::Col =>
            BigInt::ZERO,
        LatinType::Num =>
            BigInt::ZERO,
        _ =>
            panic!("non-exhaustive match")
    }
}

impl crate::HOL::Equal for LatinType {
    fn equal (x0: LatinType, x1: LatinType) -> bool {
        match (x0, x1) {
            (LatinType::Col, LatinType::Num) =>
                false,
            (LatinType::Num, LatinType::Col) =>
                false,
            (LatinType::Row, LatinType::Num) =>
                false,
            (LatinType::Num, LatinType::Row) =>
                false,
            (LatinType::Row, LatinType::Col) =>
                false,
            (LatinType::Col, LatinType::Row) =>
                false,
            (LatinType::Num, LatinType::Num) =>
                true,
            (LatinType::Col, LatinType::Col) =>
                true,
            (LatinType::Row, LatinType::Row) =>
                true,
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

pub fn random_latin_type
    (i: Natural) -> Rc<dyn Fn((Natural, Natural)) -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))> {
    (({
        let i_cap = i.clone();
        Rc::new(move |a: (Natural, Natural)| -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
            random_aux_latin_type(i_cap.clone(), i_cap.clone(), a.clone())
        })
    }) as Rc<dyn Fn((Natural, Natural)) -> ((LatinType, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
}

pub fn term_of_latin_type (x0: LatinType) -> Term {
    match x0 {
        LatinType::Row =>
            Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil))),
        LatinType::Col =>
            Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil))),
        LatinType::Num =>
            Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil))),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn typerep_latin_type (x0: Itself<LatinType>) -> Typerep {
    Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil))
}

pub fn narrowing_latin_type (x: BigInt) -> NarrowingCons<LatinType> {
    sum(((Rc::new(move |a: BigInt| -> NarrowingCons<LatinType> {
        cons(LatinType::Row, a.clone())
    })) as Rc<dyn Fn(BigInt) -> NarrowingCons<LatinType>>), ((Rc::new(move |a: BigInt| -> NarrowingCons<LatinType> {
        sum(((Rc::new(move |aa: BigInt| -> NarrowingCons<LatinType> {
            cons(LatinType::Col, aa.clone())
        })) as Rc<dyn Fn(BigInt) -> NarrowingCons<LatinType>>), ((Rc::new(move |aa: BigInt| -> NarrowingCons<LatinType> {
            cons(LatinType::Num, aa.clone())
        })) as Rc<dyn Fn(BigInt) -> NarrowingCons<LatinType>>), a.clone())
    })) as Rc<dyn Fn(BigInt) -> NarrowingCons<LatinType>>), x.clone())
}

pub fn full_exhaustive_latin_type
    (f: Rc<dyn Fn((LatinType, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>,
      i: Natural) -> Option<(bool, List<Term>)> {
    if <Natural as Ord>::less(<Natural as Zero>::zero(), i.clone()) {
        match (*f)((
              LatinType::Row,
              ((Rc::new(move |_: Unit| -> Term {
                  Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, true, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)))
              })) as Rc<dyn Fn(Unit) -> Term>)
          )) {
            Option::None =>
                match (*f)((
                      LatinType::Col,
                      ((Rc::new(move |_: Unit| -> Term {
                          Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)))
                      })) as Rc<dyn Fn(Unit) -> Term>)
                  )) {
                    Option::None =>
                        (*f)((
                            LatinType::Num,
                            ((Rc::new(move |_: Unit| -> Term {
                                Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil)))
                            })) as Rc<dyn Fn(Unit) -> Term>)
                        )),
                    Option::Some (a) =>
                        Option::Some (a.clone()),
                    _ =>
                        panic!("non-exhaustive match")
                },
            Option::Some (a) =>
                Option::Some (a.clone()),
            _ =>
                panic!("non-exhaustive match")
        }
    } else {
        Option::None
    }
}

pub fn partial_term_of_latin_type
    (x0: Itself<LatinType>, x1: NarrowingTerm) -> Term {
    match x1 {
        NarrowingTerm::NarrowingVariable (_, _) =>
            Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil))),
        NarrowingTerm::NarrowingConstructor (p0, p0a) =>
            panic!("non-exhaustive match"),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn typerep_latin_type_iitn_latin_type
    (x0: Itself<LatinTypeIITNLatinType>) -> Typerep {
    Typerep::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil))
}
