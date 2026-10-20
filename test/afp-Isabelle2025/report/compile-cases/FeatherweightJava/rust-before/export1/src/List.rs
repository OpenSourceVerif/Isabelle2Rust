use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Natural;
use crate::Arith::Num;
use crate::Arith::Zero;
use crate::Arith::minus_natural;
use crate::Arith::one_natural;
use crate::Arith::suc;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::Code_Evaluation::valapp;
use crate::Fun::comp;
use crate::Fun::id;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::Option::Option;
use crate::Orderings::Ord;
use crate::Product_Type::Unit;
use crate::Product_Type::scomp;
use crate::Pure::Itself;
use crate::Quickcheck_Exhaustive::FullExhaustive;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::Quickcheck_Narrowing::PartialTermOf;
use crate::Quickcheck_Random::Random;
use crate::Quickcheck_Random::collapse;
use crate::Random::select_weight;
use crate::String::Literal;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;

use std::marker::PhantomData;

use std::rc::Rc;

impl <A : Clone + PartialTermOf + 'static> Typerep for List<A> {
    fn typerep (x0: Itself<Self>) -> Typerepa { panic!("unimplemented instance method: typerep") }
}

#[derive(Clone)]
pub enum List<A> {
    Nil,
    Cons (A, Box<List<A>>)
}

impl <A : Clone + Equal + 'static> Equal for List<A> {
    fn equal (x0: List<A>, x1: List<A>) -> bool {
        match (x0, x1) {
            (List::Nil, List::Cons (_, _)) =>
                false,
            (List::Cons (_, _), List::Nil) =>
                false,
            (List::Cons (x21, p0), List::Cons (y21, p1)) =>
                {
                    let x22 = *p0;
                    let y22 = *p1;
                    eq(x21.clone(), y21.clone()) &&
                      <List<A> as Equal>::equal(x22.clone(), y22.clone())
                },
            (List::Nil, List::Nil) =>
                true,
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

pub fn fold <B, A> (f: Rc<dyn Fn(A, B) -> B>, x1: List<A>, s: B) -> B
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1, s) {
        (f, List::Cons (x, p0), s) =>
            {
                let xs = *p0;
                fold(f.clone(), xs.clone(), (*f)(x.clone(), s.clone()))
            },
        (_, List::Nil, s) =>
            s.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rev <A> (xs: List<A>) -> List<A>
where
    A : Clone + 'static
{
    fold(((Rc::new(move |a: A, b: List<A>| -> List<A> {
        List::Cons (a.clone(), Box::new(b.clone()))
    })) as Rc<dyn Fn(A, List<A>) -> List<A>>), xs.clone(), List::Nil)
}

pub fn zip <B, A> (x0: List<A>, x1: List<B>) -> List<(A, B)>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (x0, x1) {
        (List::Cons (x, p0), List::Cons (y, p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                List::Cons ((x.clone(), y.clone()), Box::new(zip(xs.clone(), ys.clone())))
            },
        (_, List::Nil) =>
            List::Nil,
        (List::Nil, _) =>
            List::Nil,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn foldr <B, A>
    (f: Rc<dyn Fn(A, B) -> B>, x1: List<A>) -> Rc<dyn Fn(B) -> B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (_, List::Nil) =>
            ((Rc::new(move |a: B| -> B {
                id(a.clone())
            })) as Rc<dyn Fn(B) -> B>),
        (f, List::Cons (x, p0)) =>
            {
                let xs = *p0;
                (({
                    let xs_cap = xs.clone();
                    let x_cap = x.clone();
                    let f_cap = f.clone();
                    Rc::new(move |a: B| -> B {
                        (*comp((({
                            let x_capa = x_cap.clone();
                            let f_capa = f_cap.clone();
                            Rc::new(move |b: B| -> B {
                                (*f_capa)(x_capa.clone(), b.clone())
                            })
                        }) as Rc<dyn Fn(B) -> B>), (({
                            let xs_capa = xs_cap.clone();
                            let f_capa = f_cap.clone();
                            Rc::new(move |aa: B| -> B {
                                (*foldr(f_capa.clone(), xs_capa.clone()))(aa.clone())
                            })
                        }) as Rc<dyn Fn(B) -> B>)))(a.clone())
                    })
                }) as Rc<dyn Fn(B) -> B>)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn append <A> (x0: List<A>, ys: List<A>) -> List<A>
where
    A : Clone + 'static
{
    match (x0, ys) {
        (List::Nil, ys) =>
            ys.clone(),
        (List::Cons (x, p0), ys) =>
            {
                let xs = *p0;
                List::Cons (x.clone(), Box::new(append(xs.clone(), ys.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn hd <A> (x0: List<A>) -> A
where
    A : Clone + 'static
{
    match x0 {
        List::Cons (x21, _) =>
            x21.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn tl <A> (x0: List<A>) -> List<A>
where
    A : Clone + 'static
{
    match x0 {
        List::Nil =>
            List::Nil,
        List::Cons (_, p0) =>
            {
                let x22 = *p0;
                x22.clone()
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn mapa <B, A> (f: Rc<dyn Fn(A) -> B>, x1: List<A>) -> List<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (_, List::Nil) =>
            List::Nil,
        (f, List::Cons (x21, p0)) =>
            {
                let x22 = *p0;
                List::Cons ((*f)(x21.clone()), Box::new(mapa(f.clone(), x22.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn gen_length <A> (n: BigInt, x1: List<A>) -> BigInt
where
    A : Clone + 'static
{
    match (n, x1) {
        (n, List::Cons (_, p0)) =>
            {
                let xs = *p0;
                gen_length(suc(n.clone()), xs.clone())
            },
        (n, List::Nil) =>
            n.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_list <A> (x: Rc<dyn Fn(A) -> BigInt>, xa1: List<A>) -> BigInt
where
    A : Clone + 'static
{
    match (x, xa1) {
        (_, List::Nil) =>
            BigInt::ZERO,
        (x, List::Cons (x21, p0)) =>
            {
                let x22 = *p0;
                (*x)(x21.clone()) + size_list(x.clone(), x22.clone()) +
                  suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn random_aux_list <A>
    (i: Natural, j: Natural,
      s: (Natural, Natural)) -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))
where
    A : Clone + Random + 'static
{
    (*collapse((({
        let j_cap = j.clone();
        let i_cap = i.clone();
        Rc::new(move |a: (Natural, Natural)| -> (Rc<dyn Fn((Natural, Natural)) -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>, (Natural, Natural)) {
            (*select_weight(List::Cons ((i_cap.clone(), (({
                let i_capa = i_cap.clone();
                let j_capa = j_cap.clone();
                Rc::new(move |aa: (Natural, Natural)| -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                    (*scomp(
                        (({
                            let j_capb = j_capa.clone();
                            Rc::new(move |ab: (Natural, Natural)| -> ((A, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                                <A as Random>::random(j_capb.clone(), ab.clone())
                            })
                        }) as Rc<dyn Fn((Natural, Natural)) -> ((A, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
                        (({
                            let j_capb = j_capa.clone();
                            let i_capb = i_capa.clone();
                            Rc::new(move |x: (A, Rc<dyn Fn(Unit) -> Term>), eta_arg: (Natural, Natural)| -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                                (*scomp(
                                    (({
                                        let j_capc = j_capb.clone();
let i_capc = i_capb.clone();
Rc::new(move |ab: (Natural, Natural)| -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
    random_aux_list::<A>(minus_natural(i_capc.clone(), one_natural()), j_capc.clone(), ab.clone())
})
                                    }) as Rc<dyn Fn((Natural, Natural)) -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
                                    (({
                                        let x_cap = x.clone();
Rc::new(move |y: (List<A>, Rc<dyn Fn(Unit) -> Term>), eta_arh: (Natural, Natural)| -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
    (valapp(valapp((
        ((Rc::new(move |boundary_arg: A| {
            (({
                let boundary_arg_cap = boundary_arg.clone();
                Rc::new(move |boundary_arh: List<A>| -> List<A> {
                    List::Cons (boundary_arg_cap.clone(), Box::new(boundary_arh.clone()))
                })
            }) as Rc<dyn Fn(List<A>) -> List<A>>)
        })) as Rc<dyn Fn(A) -> Rc<dyn Fn(List<A>) -> List<A>>>),
        ((Rc::new(move |_: Unit| -> Term {
            Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))
        })) as Rc<dyn Fn(Unit) -> Term>)
    ), x_cap.clone()), y.clone()), eta_arh.clone())
})
                                    }) as Rc<dyn Fn((List<A>, Rc<dyn Fn(Unit) -> Term>),
             (Natural, Natural)) -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
                                ))(eta_arg.clone())
                            })
                        }) as Rc<dyn Fn((A, Rc<dyn Fn(Unit) -> Term>),
 (Natural, Natural)) -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
                    ))(aa.clone())
                })
            }) as Rc<dyn Fn((Natural, Natural)) -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)), Box::new(List::Cons ((one_natural(), ((Rc::new(move |aa: (Natural, Natural)| -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                                       ((
                                           List::Nil,
   ((Rc::new(move |_: Unit| -> Term {
       Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))))
   })) as Rc<dyn Fn(Unit) -> Term>)
                                       ), aa.clone())
                                   })) as Rc<dyn Fn((Natural, Natural)) -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)), Box::new(List::Nil))))))(a.clone())
        })
    }) as Rc<dyn Fn((Natural, Natural)) -> (Rc<dyn Fn((Natural, Natural)) -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>, (Natural, Natural))>)))(s.clone())
}

pub fn size_lista <A> (x: List<A>) -> BigInt
where
    A : Clone + 'static
{
    gen_length(BigInt::ZERO, x.clone())
}

impl <A : Clone + Random + 'static> Random for List<A> {
    fn random
        (i: Natural,
          eta_arg_0: (Natural, Natural)) -> ((List<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
        random_aux_list::<A>(i.clone(), i.clone(), eta_arg_0.clone())
    }
}

impl <A : Clone + TermOf + 'static> TermOf for List<A> {
    fn term_of (x0: List<A>) -> Term {
        match x0 {
            List::Nil =>
                Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))),
            List::Cons (a, p0) =>
                {
                    let b = *p0;
                    Term::App (Box::new(Term::App (Box::new(Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))), Box::new(<A as TermOf>::term_of(a.clone())))), Box::new(<List<A> as TermOf>::term_of(b.clone())))
                },
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl <A : Clone + TermOf + FullExhaustive + 'static> FullExhaustive for
    List<A> {
    fn full_exhaustive
        (f: Rc<dyn Fn((List<A>, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>,
          i: Natural) -> Option<(bool, List<Term>)> {
        if <Natural as Ord>::less(<Natural as Zero>::zero(), i.clone()) {
            match (*f)((
                  List::Nil,
                  ((Rc::new(move |_: Unit| -> Term {
                      Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))))
                  })) as Rc<dyn Fn(Unit) -> Term>)
              )) {
                Option::None =>
                    <A as FullExhaustive>::full_exhaustive(
                        (({
                            let i_cap = i.clone();
                            let f_cap = f.clone();
                            Rc::new(move |(uu, uua): (A, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
                                <List<A> as FullExhaustive>::full_exhaustive(
                                    (({
                                        let uua_cap = uua.clone();
let uu_cap = uu.clone();
let f_capa = f_cap.clone();
Rc::new(move |(uub, uuc): (List<A>, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
    (*f_capa)((
        List::Cons (uu_cap.clone(), Box::new(uub.clone())),
        (({
            let uuc_cap = uuc.clone();
            let uua_capa = uua_cap.clone();
            Rc::new(move |_: Unit| -> Term {
                Term::App (Box::new(Term::App (Box::new(Term::Const (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, false, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))), Box::new((*uua_capa)(Unit::Unity)))), Box::new((*uuc_cap)(Unit::Unity)))
            })
        }) as Rc<dyn Fn(Unit) -> Term>)
    ))
})
                                    }) as Rc<dyn Fn((List<A>, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
                                    minus_natural(i_cap.clone(), one_natural())
                                )
                            })
                        }) as Rc<dyn Fn((A, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
                        minus_natural(i.clone(), one_natural())
                    ),
                Option::Some (a) =>
                    Option::Some (a.clone()),
                _ =>
                    panic!("non-exhaustive match")
            }
        } else {
            Option::None
        }
    }
}

impl <A : Clone + PartialTermOf + 'static> PartialTermOf for List<A> {
    fn partial_term_of (x0: Itself<List<A>>, x1: NarrowingTerm) -> Term {
        match x1 {
            NarrowingTerm::NarrowingVariable (_, _) =>
                Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))),
            NarrowingTerm::NarrowingConstructor (p0, p0a) =>
                panic!("non-exhaustive match"),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
