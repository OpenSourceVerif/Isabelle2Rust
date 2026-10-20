use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Natural;
use crate::Arith::Num;
use crate::Arith::suc;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::Code_Evaluation::valapp;
use crate::Execute::class_typing_i_i;
use crate::Execute::fields_i_i_i;
use crate::Execute::mbody_i_i_i_i_i;
use crate::Execute::method_typing_i_i_i;
use crate::Execute::method_typings_i_i_i;
use crate::Execute::mtype_i_i_i_i_i;
use crate::Execute::reduction_i_i_i;
use crate::Execute::reductions_i_i_i;
use crate::Execute::subtyping_i_i_i;
use crate::Execute::subtypings_i_i_i;
use crate::Execute::typing_i_i_i_i;
use crate::Execute::typings_i_i_i_i;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::hd;
use crate::List::mapa;
use crate::List::size_list;
use crate::List::tl;
use crate::Option::Option;
use crate::Predicate::Pred;
use crate::Predicate::holds;
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

use std::marker::PhantomData;

use std::rc::Rc;

#[derive(Clone)]
pub enum Exp {
    Var (BigInt),
    FieldProj (Box<Exp>, BigInt),
    MethodInvk (Box<Exp>, BigInt, Box<List<Exp>>),
    New (BigInt, Box<List<Exp>>),
    Cast (BigInt, Box<Exp>)
}

impl Typerep for Exp {
    fn typerep (x0: Itself<Exp>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))), Box::new(List::Nil))
    }
}

#[derive(Clone)]
pub enum VarDefExt<A> {
    VarDefExt (BigInt, BigInt, A)
}

impl <A : Clone + Equal + 'static> Equal for VarDefExt<A> {
    fn equal (x0: VarDefExt<A>, x1: VarDefExt<A>) -> bool {
        let (VarDefExt::VarDefExt (vdNamea, vdTypea, morea), VarDefExt::VarDefExt (vdName, vdType, more)) = (x0,
                               x1);
        vdNamea.clone() == vdName.clone() &&
          (vdTypea.clone() == vdType.clone() && eq(morea.clone(), more.clone()))
    }
}

impl <A : Clone + Typerep + 'static> Typerep for VarDefExt<A> {
    fn typerep (x0: Itself<VarDefExt<A>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))
    }
}

impl <A : Clone + Typerep + TermOf + 'static> TermOf for VarDefExt<A> {
    fn term_of (x0: VarDefExt<A>) -> Term {
        let VarDefExt::VarDefExt (a, b, c) = x0;
        Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::Const (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))), Box::new(<BigInt as TermOf>::term_of(a.clone())))), Box::new(<BigInt as TermOf>::term_of(b.clone())))), Box::new(<A as TermOf>::term_of(c.clone())))
    }
}

impl <A : Clone + Typerep + Random + 'static> Random for VarDefExt<A> {
    fn random
        (i: Natural,
          eta_arg_0: (Natural, Natural)) -> ((VarDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
        (*scomp(
            (({
                let i_cap = i.clone();
                Rc::new(move |a: (Natural, Natural)| -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                    <BigInt as Random>::random(i_cap.clone(), a.clone())
                })
            }) as Rc<dyn Fn((Natural, Natural)) -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
            (({
                let i_cap = i.clone();
                Rc::new(move |x: (BigInt, Rc<dyn Fn(Unit) -> Term>), eta_arg: (Natural, Natural)| -> ((VarDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
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
                            Rc::new(move |y: (BigInt, Rc<dyn Fn(Unit) -> Term>), eta_arh: (Natural, Natural)| -> ((VarDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                                (*scomp(
                                    (({
                                        let i_capb = i_capa.clone();
Rc::new(move |a: (Natural, Natural)| -> ((A, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
    <A as Random>::random(i_capb.clone(), a.clone())
})
                                    }) as Rc<dyn Fn((Natural, Natural)) -> ((A, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
                                    (({
                                        let y_cap = y.clone();
let x_capa = x_cap.clone();
Rc::new(move |z: (A, Rc<dyn Fn(Unit) -> Term>), eta_ari: (Natural, Natural)| -> ((VarDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
    (valapp(valapp(valapp((
        ((Rc::new(move |boundary_arg: BigInt| {
            (({
                let boundary_arg_cap = boundary_arg.clone();
                Rc::new(move |boundary_arh: BigInt| {
                    (({
                        let boundary_arh_cap = boundary_arh.clone();
                        let boundary_arg_capa = boundary_arg_cap.clone();
                        Rc::new(move |boundary_ari: A| -> VarDefExt<A> {
                            (*{
                                let boundary_arg_capb = boundary_arg_capa.clone();
                                Rc::new(move |boundary_arha: BigInt, boundary_aria: A| {
                                    VarDefExt::VarDefExt (boundary_arg_capb.clone(), boundary_arha.clone(), boundary_aria.clone())
                                })
                            })(boundary_arh_cap.clone(), boundary_ari.clone())
                        })
                    }) as Rc<dyn Fn(A) -> VarDefExt<A>>)
                })
            }) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(A) -> VarDefExt<A>>>)
        })) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(BigInt) -> Rc<dyn Fn(A) -> VarDefExt<A>>>>),
        ((Rc::new(move |_: Unit| -> Term {
            Term::Const (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))
        })) as Rc<dyn Fn(Unit) -> Term>)
    ), x_capa.clone()), y_cap.clone()), z.clone()), eta_ari.clone())
})
                                    }) as Rc<dyn Fn((A, Rc<dyn Fn(Unit) -> Term>),
             (Natural, Natural)) -> ((VarDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
                                ))(eta_arh.clone())
                            })
                        }) as Rc<dyn Fn((BigInt, Rc<dyn Fn(Unit) -> Term>),
 (Natural, Natural)) -> ((VarDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
                    ))(eta_arg.clone())
                })
            }) as Rc<dyn Fn((BigInt, Rc<dyn Fn(Unit) -> Term>),
                             (Natural, Natural)) -> ((VarDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
        ))(eta_arg_0.clone())
    }
}

impl <A : Clone + Typerep + PartialTermOf + 'static> PartialTermOf for
    VarDefExt<A> {
    fn partial_term_of (x0: Itself<VarDefExt<A>>, x1: NarrowingTerm) -> Term {
        match x1 {
            NarrowingTerm::NarrowingVariable (_, _) =>
                Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))),
            NarrowingTerm::NarrowingConstructor (p0, p0a) =>
                panic!("non-exhaustive match"),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl <A : Clone + TermOf + Typerep + FullExhaustive + 'static>
    FullExhaustive for VarDefExt<A> {
    fn full_exhaustive
        (f: Rc<dyn Fn((VarDefExt<A>, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>,
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
                                <A as FullExhaustive>::full_exhaustive(
                                    (({
                                        let y_cap = y.clone();
let x_capa = x_cap.clone();
let f_capb = f_capa.clone();
Rc::new(move |z: (A, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
    (*f_capb)(valapp(valapp(valapp((
        ((Rc::new(move |boundary_arg: BigInt| {
            (({
                let boundary_arg_cap = boundary_arg.clone();
                Rc::new(move |boundary_arh: BigInt| {
                    (({
                        let boundary_arh_cap = boundary_arh.clone();
                        let boundary_arg_capa = boundary_arg_cap.clone();
                        Rc::new(move |boundary_ari: A| -> VarDefExt<A> {
                            (*{
                                let boundary_arg_capb = boundary_arg_capa.clone();
                                Rc::new(move |boundary_arha: BigInt, boundary_aria: A| {
                                    VarDefExt::VarDefExt (boundary_arg_capb.clone(), boundary_arha.clone(), boundary_aria.clone())
                                })
                            })(boundary_arh_cap.clone(), boundary_ari.clone())
                        })
                    }) as Rc<dyn Fn(A) -> VarDefExt<A>>)
                })
            }) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(A) -> VarDefExt<A>>>)
        })) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(BigInt) -> Rc<dyn Fn(A) -> VarDefExt<A>>>>),
        ((Rc::new(move |_: Unit| -> Term {
            Term::Const (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))
        })) as Rc<dyn Fn(Unit) -> Term>)
    ), x_capa.clone()), y_cap.clone()), z.clone()))
})
                                    }) as Rc<dyn Fn((A, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
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

#[derive(Clone)]
pub enum MethodDefExt<A> {
    MethodDefExt (BigInt, BigInt, List<VarDefExt<Unit>>, Exp, A)
}

impl <A : Clone + Equal + 'static> Equal for MethodDefExt<A> {
    fn equal (x0: MethodDefExt<A>, x1: MethodDefExt<A>) -> bool {
        let (MethodDefExt::MethodDefExt (mReturna, mNamea, mParamsa, mBodya, morea), MethodDefExt::MethodDefExt (mReturn, mName, mParams, mBody, more)) = (x0,
                                     x1);
        mReturna.clone() == mReturn.clone() &&
          (mNamea.clone() == mName.clone() &&
            (<List<VarDefExt<Unit>> as Equal>::equal(mParamsa.clone(), mParams.clone()) &&
              (<Exp as Equal>::equal(mBodya.clone(), mBody.clone()) &&
                eq(morea.clone(), more.clone()))))
    }
}

impl <A : Clone + Typerep + 'static> Typerep for MethodDefExt<A> {
    fn typerep (x0: Itself<MethodDefExt<A>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))
    }
}

impl <A : Clone + Typerep + TermOf + 'static> TermOf for MethodDefExt<A> {
    fn term_of (x0: MethodDefExt<A>) -> Term {
        let MethodDefExt::MethodDefExt (a, b, c, d, e) = x0;
        Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::Const (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))), Box::new(<BigInt as TermOf>::term_of(a.clone())))), Box::new(<BigInt as TermOf>::term_of(b.clone())))), Box::new(<List<VarDefExt<Unit>> as TermOf>::term_of(c.clone())))), Box::new(<Exp as TermOf>::term_of(d.clone())))), Box::new(<A as TermOf>::term_of(e.clone())))
    }
}

impl <A : Clone + Typerep + PartialTermOf + 'static> PartialTermOf for
    MethodDefExt<A> {
    fn partial_term_of
        (x0: Itself<MethodDefExt<A>>, x1: NarrowingTerm) -> Term {
        match x1 {
            NarrowingTerm::NarrowingVariable (_, _) =>
                Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))),
            NarrowingTerm::NarrowingConstructor (p0, p0a) =>
                panic!("non-exhaustive match"),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

#[derive(Clone)]
pub struct ExpPreExp<A>(PhantomData<A>);

#[derive(Clone)]
pub struct ExpIITNExp ;

#[derive(Clone)]
pub enum ConstructorDefExt<A> {
    ConstructorDefExt (BigInt, List<VarDefExt<Unit>>, List<BigInt>, List<BigInt>, A)
}

#[derive(Clone)]
pub enum ClassDefExt<A> {
    ClassDefExt (BigInt, BigInt, List<VarDefExt<Unit>>, ConstructorDefExt<Unit>, List<MethodDefExt<Unit>>, A)
}

#[derive(Clone)]
pub struct
  N2mExpSubstsPreN2mExp<A, B, C>(PhantomData<A>, PhantomData<B>,
                                   PhantomData<C>);

pub fn this () -> BigInt {
    BigInt::ZERO
}

pub fn mbody
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, x2: BigInt,
      x3: BigInt, x4: List<BigInt>, x5: Exp) -> bool {
    holds(mbody_i_i_i_i_i(x1.clone(), x2.clone(), x3.clone(), x4.clone(), x5.clone()))
}

pub fn mtype
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, x2: BigInt,
      x3: BigInt, x4: List<BigInt>, x5: BigInt) -> bool {
    holds(mtype_i_i_i_i_i(x1.clone(), x2.clone(), x3.clone(), x4.clone(), x5.clone()))
}

pub fn objecta () -> BigInt {
    BigInt::ZERO
}

pub fn fields
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, x2: BigInt,
      x3: List<VarDefExt<Unit>>) -> bool {
    holds(fields_i_i_i(x1.clone(), x2.clone(), x3.clone()))
}

pub fn lookup <A> (x0: List<A>, p: Rc<dyn Fn(A) -> bool>) -> Option<A>
where
    A : Clone + 'static
{
    match (x0, p) {
        (List::Nil, _) =>
            Option::None,
        (List::Cons (h, p0), p) =>
            {
                let t = *p0;
                if (*p)(h.clone()) {
                    Option::Some (h.clone())
                } else {
                    lookup(t.clone(), p.clone())
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn substs (sigma: Rc<dyn Fn(BigInt) -> Option<Exp>>, x1: Exp) -> Exp {
    match (sigma, x1) {
        (sigma, Exp::Var (x)) =>
            match (*sigma)(x.clone()) {
                Option::None =>
                    Exp::Var (x.clone()),
                Option::Some (p) =>
                    p.clone(),
                _ =>
                    panic!("non-exhaustive match")
            },
        (sigma, Exp::FieldProj (p0, f)) =>
            {
                let e = *p0;
                Exp::FieldProj (Box::new(substs(sigma.clone(), e.clone())), f.clone())
            },
        (sigma, Exp::MethodInvk (p0, m, p1)) =>
            {
                let e = *p0;
                let es = *p1;
                Exp::MethodInvk (Box::new(substs(sigma.clone(), e.clone())), m.clone(), Box::new(subst_list1(sigma.clone(), es.clone())))
            },
        (sigma, Exp::New (c, p0)) =>
            {
                let es = *p0;
                Exp::New (c.clone(), Box::new(subst_list2(sigma.clone(), es.clone())))
            },
        (sigma, Exp::Cast (c, p0)) =>
            {
                let e = *p0;
                Exp::Cast (c.clone(), Box::new(substs(sigma.clone(), e.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn subst_list1
    (sigma: Rc<dyn Fn(BigInt) -> Option<Exp>>, x1: List<Exp>) -> List<Exp> {
    match (sigma, x1) {
        (_, List::Nil) =>
            List::Nil,
        (sigma, List::Cons (h, p0)) =>
            {
                let t = *p0;
                List::Cons (substs(sigma.clone(), h.clone()), Box::new(subst_list1(sigma.clone(), t.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn subst_list2
    (sigma: Rc<dyn Fn(BigInt) -> Option<Exp>>, x1: List<Exp>) -> List<Exp> {
    match (sigma, x1) {
        (_, List::Nil) =>
            List::Nil,
        (sigma, List::Cons (h, p0)) =>
            {
                let t = *p0;
                List::Cons (substs(sigma.clone(), h.clone()), Box::new(subst_list2(sigma.clone(), t.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn typing
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      x2: Rc<dyn Fn(BigInt) -> Option<BigInt>>, x3: Exp, x4: BigInt) -> bool {
    holds(typing_i_i_i_i(x1.clone(), x2.clone(), x3.clone(), x4.clone()))
}

pub fn lookup2 <B, A>
    (x0: List<A>, l2: List<B>, p: Rc<dyn Fn(A) -> bool>) -> Option<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (x0, l2, p) {
        (List::Nil, _, _) =>
            Option::None,
        (List::Cons (h1, p0), l2, p) =>
            {
                let t1 = *p0;
                if (*p)(h1.clone()) {
                    Option::Some (hd(l2.clone()))
                } else {
                    lookup2(t1.clone(), tl(l2.clone()), p.clone())
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn typings
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      x2: Rc<dyn Fn(BigInt) -> Option<BigInt>>, x3: List<Exp>,
      x4: List<BigInt>) -> bool {
    holds(typings_i_i_i_i(x1.clone(), x2.clone(), x3.clone(), x4.clone()))
}

pub fn reduction
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, x2: Exp,
      x3: Exp) -> bool {
    holds(reduction_i_i_i(x1.clone(), x2.clone(), x3.clone()))
}

pub fn subtyping
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, x2: BigInt,
      x3: BigInt) -> bool {
    holds(subtyping_i_i_i(x1.clone(), x2.clone(), x3.clone()))
}

pub fn reductions
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, x2: Exp,
      x3: Exp) -> bool {
    holds(reductions_i_i_i(x1.clone(), x2.clone(), x3.clone()))
}

pub fn subtypings
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>, x2: List<BigInt>,
      x3: List<BigInt>) -> bool {
    holds(subtypings_i_i_i(x1.clone(), x2.clone(), x3.clone()))
}

pub fn rec_exp <A>
    (f1: Rc<dyn Fn(BigInt) -> A>, f2: Rc<dyn Fn(Exp, BigInt, A) -> A>,
      f3: Rc<dyn Fn(Exp, BigInt, List<(Exp, A)>, A) -> A>,
      f4: Rc<dyn Fn(BigInt, List<(Exp, A)>) -> A>,
      f5: Rc<dyn Fn(BigInt, Exp, A) -> A>, x5: Exp) -> A
where
    A : Clone + 'static
{
    match (f1, f2, f3, f4, f5, x5) {
        (f1, _, _, _, _, Exp::Var (x1)) =>
            (*f1)(x1.clone()),
        (f1, f2, f3, f4, f5, Exp::FieldProj (p0, x22)) =>
            {
                let x21 = *p0;
                (*f2)(x21.clone(), x22.clone(), rec_exp(f1.clone(), f2.clone(), f3.clone(), f4.clone(), f5.clone(), x21.clone()))
            },
        (f1, f2, f3, f4, f5, Exp::MethodInvk (p0, x32, p1)) =>
            {
                let x31 = *p0;
                let x33 = *p1;
                (*f3)(x31.clone(), x32.clone(), mapa(
                    (({
                        let f5_cap = f5.clone();
                        let f4_cap = f4.clone();
                        let f3_cap = f3.clone();
                        let f2_cap = f2.clone();
                        let f1_cap = f1.clone();
                        Rc::new(move |exp: Exp| -> (Exp, A) {
                            (exp.clone(), rec_exp(f1_cap.clone(), f2_cap.clone(), f3_cap.clone(), f4_cap.clone(), f5_cap.clone(), exp.clone()))
                        })
                    }) as Rc<dyn Fn(Exp) -> (Exp, A)>),
                    x33.clone()
                ), rec_exp(f1.clone(), f2.clone(), f3.clone(), f4.clone(), f5.clone(), x31.clone()))
            },
        (f1, f2, f3, f4, f5, Exp::New (x41, p0)) =>
            {
                let x42 = *p0;
                (*f4)(x41.clone(), mapa(
                    (({
                        let f5_cap = f5.clone();
                        let f4_cap = f4.clone();
                        let f3_cap = f3.clone();
                        let f2_cap = f2.clone();
                        let f1_cap = f1.clone();
                        Rc::new(move |exp: Exp| -> (Exp, A) {
                            (exp.clone(), rec_exp(f1_cap.clone(), f2_cap.clone(), f3_cap.clone(), f4_cap.clone(), f5_cap.clone(), exp.clone()))
                        })
                    }) as Rc<dyn Fn(Exp) -> (Exp, A)>),
                    x42.clone()
                ))
            },
        (f1, f2, f3, f4, f5, Exp::Cast (x51, p0)) =>
            {
                let x52 = *p0;
                (*f5)(x51.clone(), x52.clone(), rec_exp(f1.clone(), f2.clone(), f3.clone(), f4.clone(), f5.clone(), x52.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn make (vdName: BigInt, vdType: BigInt) -> VarDefExt<Unit> {
    VarDefExt::VarDefExt (vdName.clone(), vdType.clone(), Unit::Unity)
}

pub fn more <A> (x0: VarDefExt<A>) -> A
where
    A : Clone + 'static
{
    let VarDefExt::VarDefExt (_, _, more) = x0;
    more.clone()
}

pub fn class_typing
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      x2: ClassDefExt<Unit>) -> bool {
    holds(class_typing_i_i(x1.clone(), x2.clone()))
}

pub fn size_exp (x0: Exp) -> BigInt {
    match x0 {
        Exp::Var (_) =>
            BigInt::ZERO,
        Exp::FieldProj (p0, _) =>
            {
                let x21 = *p0;
                size_exp(x21.clone()) + suc(BigInt::ZERO)
            },
        Exp::MethodInvk (p0, _, p1) =>
            {
                let x31 = *p0;
                let x33 = *p1;
                size_list(((Rc::new(move |a: Exp| -> BigInt {
                      size_exp(a.clone())
                  })) as Rc<dyn Fn(Exp) -> BigInt>), x33.clone()) +
                  size_exp(x31.clone()) +
                  suc(BigInt::ZERO)
            },
        Exp::New (_, p0) =>
            {
                let x42 = *p0;
                size_list(((Rc::new(move |a: Exp| -> BigInt {
                      size_exp(a.clone())
                  })) as Rc<dyn Fn(Exp) -> BigInt>), x42.clone()) +
                  suc(BigInt::ZERO)
            },
        Exp::Cast (_, p0) =>
            {
                let x52 = *p0;
                size_exp(x52.clone()) + suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn makea
    (cName: BigInt, cSuper: BigInt, cFields: List<VarDefExt<Unit>>,
      cConstructor: ConstructorDefExt<Unit>,
      cMethods: List<MethodDefExt<Unit>>) -> ClassDefExt<Unit> {
    ClassDefExt::ClassDefExt (cName.clone(), cSuper.clone(), cFields.clone(), cConstructor.clone(), cMethods.clone(), Unit::Unity)
}

pub fn morea <A> (x0: ClassDefExt<A>) -> A
where
    A : Clone + 'static
{
    let ClassDefExt::ClassDefExt (_, _, _, _, _, more) = x0;
    more.clone()
}

pub fn method_typing
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      x2: MethodDefExt<Unit>, x3: BigInt) -> bool {
    holds(method_typing_i_i_i(x1.clone(), x2.clone(), x3.clone()))
}

pub fn vd_type <A> (x0: VarDefExt<A>) -> BigInt
where
    A : Clone + 'static
{
    let VarDefExt::VarDefExt (_, vdType, _) = x0;
    vdType.clone()
}

pub fn vd_name <A> (x0: VarDefExt<A>) -> BigInt
where
    A : Clone + 'static
{
    let VarDefExt::VarDefExt (vdName, _, _) = x0;
    vdName.clone()
}

pub fn extend <A> (r: VarDefExt<Unit>, more: A) -> VarDefExt<A>
where
    A : Clone + 'static
{
    VarDefExt::VarDefExt (vd_name(r.clone()), vd_type(r.clone()), more.clone())
}

pub fn fieldsa (vdName: BigInt, vdType: BigInt) -> VarDefExt<Unit> {
    VarDefExt::VarDefExt (vdName.clone(), vdType.clone(), Unit::Unity)
}

pub fn var_defs_names (x: List<VarDefExt<Unit>>) -> List<BigInt> {
    mapa(((Rc::new(move |a: VarDefExt<Unit>| -> BigInt {
        vd_name(a.clone())
    })) as Rc<dyn Fn(VarDefExt<Unit>) -> BigInt>), x.clone())
}

pub fn var_defs_types (x: List<VarDefExt<Unit>>) -> List<BigInt> {
    mapa(((Rc::new(move |a: VarDefExt<Unit>| -> BigInt {
        vd_type(a.clone())
    })) as Rc<dyn Fn(VarDefExt<Unit>) -> BigInt>), x.clone())
}

pub fn c_name <A> (x0: ClassDefExt<A>) -> BigInt
where
    A : Clone + 'static
{
    let ClassDefExt::ClassDefExt (cName, _, _, _, _, _) = x0;
    cName.clone()
}

pub fn makeb
    (mReturn: BigInt, mName: BigInt, mParams: List<VarDefExt<Unit>>,
      mBody: Exp) -> MethodDefExt<Unit> {
    MethodDefExt::MethodDefExt (mReturn.clone(), mName.clone(), mParams.clone(), mBody.clone(), Unit::Unity)
}

pub fn moreb <A> (x0: MethodDefExt<A>) -> A
where
    A : Clone + 'static
{
    let MethodDefExt::MethodDefExt (_, _, _, _, more) = x0;
    more.clone()
}

pub fn method_typings
    (x1: Rc<dyn Fn(BigInt) -> Option<ClassDefExt<Unit>>>,
      x2: List<MethodDefExt<Unit>>, x3: BigInt) -> bool {
    holds(method_typings_i_i_i(x1.clone(), x2.clone(), x3.clone()))
}

pub fn c_super <A> (x0: ClassDefExt<A>) -> BigInt
where
    A : Clone + 'static
{
    let ClassDefExt::ClassDefExt (_, cSuper, _, _, _, _) = x0;
    cSuper.clone()
}

pub fn c_constructor <A> (x0: ClassDefExt<A>) -> ConstructorDefExt<Unit>
where
    A : Clone + 'static
{
    let ClassDefExt::ClassDefExt (_, _, _, cConstructor, _, _) = x0;
    cConstructor.clone()
}

pub fn c_methods <A> (x0: ClassDefExt<A>) -> List<MethodDefExt<Unit>>
where
    A : Clone + 'static
{
    let ClassDefExt::ClassDefExt (_, _, _, _, cMethods, _) = x0;
    cMethods.clone()
}

pub fn c_fields <A> (x0: ClassDefExt<A>) -> List<VarDefExt<Unit>>
where
    A : Clone + 'static
{
    let ClassDefExt::ClassDefExt (_, _, cFields, _, _, _) = x0;
    cFields.clone()
}

pub fn extenda <A> (r: ClassDefExt<Unit>, more: A) -> ClassDefExt<A>
where
    A : Clone + 'static
{
    ClassDefExt::ClassDefExt (c_name(r.clone()), c_super(r.clone()), c_fields(r.clone()), c_constructor(r.clone()), c_methods(r.clone()), more.clone())
}

pub fn fieldsb
    (cName: BigInt, cSuper: BigInt, cFields: List<VarDefExt<Unit>>,
      cConstructor: ConstructorDefExt<Unit>,
      cMethods: List<MethodDefExt<Unit>>) -> ClassDefExt<Unit> {
    ClassDefExt::ClassDefExt (cName.clone(), cSuper.clone(), cFields.clone(), cConstructor.clone(), cMethods.clone(), Unit::Unity)
}

pub fn m_body <A> (x0: MethodDefExt<A>) -> Exp
where
    A : Clone + 'static
{
    let MethodDefExt::MethodDefExt (_, _, _, mBody, _) = x0;
    mBody.clone()
}

pub fn m_name <A> (x0: MethodDefExt<A>) -> BigInt
where
    A : Clone + 'static
{
    let MethodDefExt::MethodDefExt (_, mName, _, _, _) = x0;
    mName.clone()
}

pub fn truncate <A> (r: VarDefExt<A>) -> VarDefExt<Unit>
where
    A : Clone + 'static
{
    VarDefExt::VarDefExt (vd_name(r.clone()), vd_type(r.clone()), Unit::Unity)
}

pub fn m_return <A> (x0: MethodDefExt<A>) -> BigInt
where
    A : Clone + 'static
{
    let MethodDefExt::MethodDefExt (mReturn, _, _, _, _) = x0;
    mReturn.clone()
}

pub fn m_params <A> (x0: MethodDefExt<A>) -> List<VarDefExt<Unit>>
where
    A : Clone + 'static
{
    let MethodDefExt::MethodDefExt (_, _, mParams, _, _) = x0;
    mParams.clone()
}

pub fn extendb <A> (r: MethodDefExt<Unit>, more: A) -> MethodDefExt<A>
where
    A : Clone + 'static
{
    MethodDefExt::MethodDefExt (m_return(r.clone()), m_name(r.clone()), m_params(r.clone()), m_body(r.clone()), more.clone())
}

pub fn fieldsc
    (mReturn: BigInt, mName: BigInt, mParams: List<VarDefExt<Unit>>,
      mBody: Exp) -> MethodDefExt<Unit> {
    MethodDefExt::MethodDefExt (mReturn.clone(), mName.clone(), mParams.clone(), mBody.clone(), Unit::Unity)
}

pub fn truncatea <A> (r: ClassDefExt<A>) -> ClassDefExt<Unit>
where
    A : Clone + 'static
{
    ClassDefExt::ClassDefExt (c_name(r.clone()), c_super(r.clone()), c_fields(r.clone()), c_constructor(r.clone()), c_methods(r.clone()), Unit::Unity)
}

pub fn truncateb <A> (r: MethodDefExt<A>) -> MethodDefExt<Unit>
where
    A : Clone + 'static
{
    MethodDefExt::MethodDefExt (m_return(r.clone()), m_name(r.clone()), m_params(r.clone()), m_body(r.clone()), Unit::Unity)
}

pub fn more_update <A>
    (morea: Rc<dyn Fn(A) -> A>, x1: VarDefExt<A>) -> VarDefExt<A>
where
    A : Clone + 'static
{
    let (morea, VarDefExt::VarDefExt (vdName, vdType, more)) = (morea, x1);
    VarDefExt::VarDefExt (vdName.clone(), vdType.clone(), (*morea)(more.clone()))
}

pub fn makec
    (kName: BigInt, kParams: List<VarDefExt<Unit>>, kSuper: List<BigInt>,
      kInits: List<BigInt>) -> ConstructorDefExt<Unit> {
    ConstructorDefExt::ConstructorDefExt (kName.clone(), kParams.clone(), kSuper.clone(), kInits.clone(), Unit::Unity)
}

pub fn morec <A> (x0: ConstructorDefExt<A>) -> A
where
    A : Clone + 'static
{
    let ConstructorDefExt::ConstructorDefExt (_, _, _, _, more) = x0;
    more.clone()
}

pub fn more_updatea <A>
    (morea: Rc<dyn Fn(A) -> A>, x1: ClassDefExt<A>) -> ClassDefExt<A>
where
    A : Clone + 'static
{
    let (morea, ClassDefExt::ClassDefExt (cName, cSuper, cFields, cConstructor, cMethods, more)) = (morea,
                      x1);
    ClassDefExt::ClassDefExt (cName.clone(), cSuper.clone(), cFields.clone(), cConstructor.clone(), cMethods.clone(), (*morea)(more.clone()))
}

pub fn k_name <A> (x0: ConstructorDefExt<A>) -> BigInt
where
    A : Clone + 'static
{
    let ConstructorDefExt::ConstructorDefExt (kName, _, _, _, _) = x0;
    kName.clone()
}

pub fn vd_name_update <A>
    (vdNamea: Rc<dyn Fn(BigInt) -> BigInt>, x1: VarDefExt<A>) -> VarDefExt<A>
where
    A : Clone + 'static
{
    let (vdNamea, VarDefExt::VarDefExt (vdName, vdType, more)) = (vdNamea, x1);
    VarDefExt::VarDefExt ((*vdNamea)(vdName.clone()), vdType.clone(), more.clone())
}

pub fn vd_type_update <A>
    (vdTypea: Rc<dyn Fn(BigInt) -> BigInt>, x1: VarDefExt<A>) -> VarDefExt<A>
where
    A : Clone + 'static
{
    let (vdTypea, VarDefExt::VarDefExt (vdName, vdType, more)) = (vdTypea, x1);
    VarDefExt::VarDefExt (vdName.clone(), (*vdTypea)(vdType.clone()), more.clone())
}

pub fn c_name_update <A>
    (cNamea: Rc<dyn Fn(BigInt) -> BigInt>, x1: ClassDefExt<A>) -> ClassDefExt<A>
where
    A : Clone + 'static
{
    let (cNamea, ClassDefExt::ClassDefExt (cName, cSuper, cFields, cConstructor, cMethods, more)) = (cNamea,
                       x1);
    ClassDefExt::ClassDefExt ((*cNamea)(cName.clone()), cSuper.clone(), cFields.clone(), cConstructor.clone(), cMethods.clone(), more.clone())
}

pub fn k_params <A> (x0: ConstructorDefExt<A>) -> List<VarDefExt<Unit>>
where
    A : Clone + 'static
{
    let ConstructorDefExt::ConstructorDefExt (_, kParams, _, _, _) = x0;
    kParams.clone()
}

pub fn k_super <A> (x0: ConstructorDefExt<A>) -> List<BigInt>
where
    A : Clone + 'static
{
    let ConstructorDefExt::ConstructorDefExt (_, _, kSuper, _, _) = x0;
    kSuper.clone()
}

pub fn k_inits <A> (x0: ConstructorDefExt<A>) -> List<BigInt>
where
    A : Clone + 'static
{
    let ConstructorDefExt::ConstructorDefExt (_, _, _, kInits, _) = x0;
    kInits.clone()
}

pub fn extendc <A> (r: ConstructorDefExt<Unit>, more: A) -> ConstructorDefExt<A>
where
    A : Clone + 'static
{
    ConstructorDefExt::ConstructorDefExt (k_name(r.clone()), k_params(r.clone()), k_super(r.clone()), k_inits(r.clone()), more.clone())
}

pub fn fieldsd
    (kName: BigInt, kParams: List<VarDefExt<Unit>>, kSuper: List<BigInt>,
      kInits: List<BigInt>) -> ConstructorDefExt<Unit> {
    ConstructorDefExt::ConstructorDefExt (kName.clone(), kParams.clone(), kSuper.clone(), kInits.clone(), Unit::Unity)
}

pub fn more_updateb <A>
    (morea: Rc<dyn Fn(A) -> A>, x1: MethodDefExt<A>) -> MethodDefExt<A>
where
    A : Clone + 'static
{
    let (morea, MethodDefExt::MethodDefExt (mReturn, mName, mParams, mBody, more)) = (morea,
        x1);
    MethodDefExt::MethodDefExt (mReturn.clone(), mName.clone(), mParams.clone(), mBody.clone(), (*morea)(more.clone()))
}

pub fn c_super_update <A>
    (cSupera: Rc<dyn Fn(BigInt) -> BigInt>,
      x1: ClassDefExt<A>) -> ClassDefExt<A>
where
    A : Clone + 'static
{
    let (cSupera, ClassDefExt::ClassDefExt (cName, cSuper, cFields, cConstructor, cMethods, more)) = (cSupera,
                        x1);
    ClassDefExt::ClassDefExt (cName.clone(), (*cSupera)(cSuper.clone()), cFields.clone(), cConstructor.clone(), cMethods.clone(), more.clone())
}

pub fn m_body_update <A>
    (mBodya: Rc<dyn Fn(Exp) -> Exp>, x1: MethodDefExt<A>) -> MethodDefExt<A>
where
    A : Clone + 'static
{
    let (mBodya, MethodDefExt::MethodDefExt (mReturn, mName, mParams, mBody, more)) = (mBodya,
         x1);
    MethodDefExt::MethodDefExt (mReturn.clone(), mName.clone(), mParams.clone(), (*mBodya)(mBody.clone()), more.clone())
}

pub fn m_name_update <A>
    (mNamea: Rc<dyn Fn(BigInt) -> BigInt>,
      x1: MethodDefExt<A>) -> MethodDefExt<A>
where
    A : Clone + 'static
{
    let (mNamea, MethodDefExt::MethodDefExt (mReturn, mName, mParams, mBody, more)) = (mNamea,
         x1);
    MethodDefExt::MethodDefExt (mReturn.clone(), (*mNamea)(mName.clone()), mParams.clone(), mBody.clone(), more.clone())
}

pub fn size_expa (x0: Exp) -> BigInt {
    match x0 {
        Exp::Var (_) =>
            BigInt::ZERO,
        Exp::FieldProj (p0, _) =>
            {
                let x21 = *p0;
                size_expa(x21.clone()) + suc(BigInt::ZERO)
            },
        Exp::MethodInvk (p0, _, p1) =>
            {
                let x31 = *p0;
                let x33 = *p1;
                size_list(((Rc::new(move |a: Exp| -> BigInt {
                      size_expa(a.clone())
                  })) as Rc<dyn Fn(Exp) -> BigInt>), x33.clone()) +
                  size_expa(x31.clone()) +
                  suc(BigInt::ZERO)
            },
        Exp::New (_, p0) =>
            {
                let x42 = *p0;
                size_list(((Rc::new(move |a: Exp| -> BigInt {
                      size_expa(a.clone())
                  })) as Rc<dyn Fn(Exp) -> BigInt>), x42.clone()) +
                  suc(BigInt::ZERO)
            },
        Exp::Cast (_, p0) =>
            {
                let x52 = *p0;
                size_expa(x52.clone()) + suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn c_fields_update <A>
    (cFieldsa: Rc<dyn Fn(List<VarDefExt<Unit>>) -> List<VarDefExt<Unit>>>,
      x1: ClassDefExt<A>) -> ClassDefExt<A>
where
    A : Clone + 'static
{
    let (cFieldsa, ClassDefExt::ClassDefExt (cName, cSuper, cFields, cConstructor, cMethods, more)) = (cFieldsa,
                         x1);
    ClassDefExt::ClassDefExt (cName.clone(), cSuper.clone(), (*cFieldsa)(cFields.clone()), cConstructor.clone(), cMethods.clone(), more.clone())
}

pub fn truncatec <A> (r: ConstructorDefExt<A>) -> ConstructorDefExt<Unit>
where
    A : Clone + 'static
{
    ConstructorDefExt::ConstructorDefExt (k_name(r.clone()), k_params(r.clone()), k_super(r.clone()), k_inits(r.clone()), Unit::Unity)
}

pub fn c_methods_update <A>
    (cMethodsa: Rc<dyn Fn(List<MethodDefExt<Unit>>) -> List<MethodDefExt<Unit>>>,
      x1: ClassDefExt<A>) -> ClassDefExt<A>
where
    A : Clone + 'static
{
    let (cMethodsa, ClassDefExt::ClassDefExt (cName, cSuper, cFields, cConstructor, cMethods, more)) = (cMethodsa,
                          x1);
    ClassDefExt::ClassDefExt (cName.clone(), cSuper.clone(), cFields.clone(), cConstructor.clone(), (*cMethodsa)(cMethods.clone()), more.clone())
}

pub fn m_params_update <A>
    (mParamsa: Rc<dyn Fn(List<VarDefExt<Unit>>) -> List<VarDefExt<Unit>>>,
      x1: MethodDefExt<A>) -> MethodDefExt<A>
where
    A : Clone + 'static
{
    let (mParamsa, MethodDefExt::MethodDefExt (mReturn, mName, mParams, mBody, more)) = (mParamsa,
           x1);
    MethodDefExt::MethodDefExt (mReturn.clone(), mName.clone(), (*mParamsa)(mParams.clone()), mBody.clone(), more.clone())
}

pub fn m_return_update <A>
    (mReturna: Rc<dyn Fn(BigInt) -> BigInt>,
      x1: MethodDefExt<A>) -> MethodDefExt<A>
where
    A : Clone + 'static
{
    let (mReturna, MethodDefExt::MethodDefExt (mReturn, mName, mParams, mBody, more)) = (mReturna,
           x1);
    MethodDefExt::MethodDefExt ((*mReturna)(mReturn.clone()), mName.clone(), mParams.clone(), mBody.clone(), more.clone())
}

pub fn more_updatec <A>
    (morea: Rc<dyn Fn(A) -> A>,
      x1: ConstructorDefExt<A>) -> ConstructorDefExt<A>
where
    A : Clone + 'static
{
    let (morea, ConstructorDefExt::ConstructorDefExt (kName, kParams, kSuper, kInits, more)) = (morea,
                  x1);
    ConstructorDefExt::ConstructorDefExt (kName.clone(), kParams.clone(), kSuper.clone(), kInits.clone(), (*morea)(more.clone()))
}

pub fn k_name_update <A>
    (kNamea: Rc<dyn Fn(BigInt) -> BigInt>,
      x1: ConstructorDefExt<A>) -> ConstructorDefExt<A>
where
    A : Clone + 'static
{
    let (kNamea, ConstructorDefExt::ConstructorDefExt (kName, kParams, kSuper, kInits, more)) = (kNamea,
                   x1);
    ConstructorDefExt::ConstructorDefExt ((*kNamea)(kName.clone()), kParams.clone(), kSuper.clone(), kInits.clone(), more.clone())
}

pub fn c_constructor_update <A>
    (cConstructora: Rc<dyn Fn(ConstructorDefExt<Unit>) -> ConstructorDefExt<Unit>>,
      x1: ClassDefExt<A>) -> ClassDefExt<A>
where
    A : Clone + 'static
{
    let (cConstructora, ClassDefExt::ClassDefExt (cName, cSuper, cFields, cConstructor, cMethods, more)) = (cConstructora,
                              x1);
    ClassDefExt::ClassDefExt (cName.clone(), cSuper.clone(), cFields.clone(), (*cConstructora)(cConstructor.clone()), cMethods.clone(), more.clone())
}

pub fn k_inits_update <A>
    (kInitsa: Rc<dyn Fn(List<BigInt>) -> List<BigInt>>,
      x1: ConstructorDefExt<A>) -> ConstructorDefExt<A>
where
    A : Clone + 'static
{
    let (kInitsa, ConstructorDefExt::ConstructorDefExt (kName, kParams, kSuper, kInits, more)) = (kInitsa,
                    x1);
    ConstructorDefExt::ConstructorDefExt (kName.clone(), kParams.clone(), kSuper.clone(), (*kInitsa)(kInits.clone()), more.clone())
}

pub fn k_super_update <A>
    (kSupera: Rc<dyn Fn(List<BigInt>) -> List<BigInt>>,
      x1: ConstructorDefExt<A>) -> ConstructorDefExt<A>
where
    A : Clone + 'static
{
    let (kSupera, ConstructorDefExt::ConstructorDefExt (kName, kParams, kSuper, kInits, more)) = (kSupera,
                    x1);
    ConstructorDefExt::ConstructorDefExt (kName.clone(), kParams.clone(), (*kSupera)(kSuper.clone()), kInits.clone(), more.clone())
}

pub fn k_params_update <A>
    (kParamsa: Rc<dyn Fn(List<VarDefExt<Unit>>) -> List<VarDefExt<Unit>>>,
      x1: ConstructorDefExt<A>) -> ConstructorDefExt<A>
where
    A : Clone + 'static
{
    let (kParamsa, ConstructorDefExt::ConstructorDefExt (kName, kParams, kSuper, kInits, more)) = (kParamsa,
                     x1);
    ConstructorDefExt::ConstructorDefExt (kName.clone(), (*kParamsa)(kParams.clone()), kSuper.clone(), kInits.clone(), more.clone())
}

impl <A : Clone + Typerep + 'static> Typerep for ExpPreExp<A> {
    fn typerep (x0: Itself<ExpPreExp<A>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))
    }
}

impl Typerep for ExpIITNExp {
    fn typerep (x0: Itself<ExpIITNExp>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Nil))
    }
}

impl <A : Clone + Equal + 'static> Equal for ConstructorDefExt<A> {
    fn equal (x0: ConstructorDefExt<A>, x1: ConstructorDefExt<A>) -> bool {
        let (ConstructorDefExt::ConstructorDefExt (kNamea, kParamsa, kSupera, kInitsa, morea), ConstructorDefExt::ConstructorDefExt (kName, kParams, kSuper, kInits, more)) = (x0,
                 x1);
        kNamea.clone() == kName.clone() &&
          (<List<VarDefExt<Unit>> as Equal>::equal(kParamsa.clone(), kParams.clone()) &&
            (<List<BigInt> as Equal>::equal(kSupera.clone(), kSuper.clone()) &&
              (<List<BigInt> as Equal>::equal(kInitsa.clone(), kInits.clone()) &&
                eq(morea.clone(), more.clone()))))
    }
}

impl <A : Clone + Equal + 'static> Equal for ClassDefExt<A> {
    fn equal (x0: ClassDefExt<A>, x1: ClassDefExt<A>) -> bool {
        let (ClassDefExt::ClassDefExt (cNamea, cSupera, cFieldsa, cConstructora, cMethodsa, morea), ClassDefExt::ClassDefExt (cName, cSuper, cFields, cConstructor, cMethods, more)) = (x0,
                          x1);
        cNamea.clone() == cName.clone() &&
          (cSupera.clone() == cSuper.clone() &&
            (<List<VarDefExt<Unit>> as Equal>::equal(cFieldsa.clone(), cFields.clone()) &&
              (<ConstructorDefExt<Unit> as Equal>::equal(cConstructora.clone(), cConstructor.clone()) &&
                (<List<MethodDefExt<Unit>> as Equal>::equal(cMethodsa.clone(), cMethods.clone()) &&
                  eq(morea.clone(), more.clone())))))
    }
}

impl <A : Clone + Typerep + TermOf + 'static> TermOf for ConstructorDefExt<A> {
    fn term_of (x0: ConstructorDefExt<A>) -> Term {
        let ConstructorDefExt::ConstructorDefExt (a, b, c, d, e) = x0;
        Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::Const (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))), Box::new(<BigInt as TermOf>::term_of(a.clone())))), Box::new(<List<VarDefExt<Unit>> as TermOf>::term_of(b.clone())))), Box::new(<List<BigInt> as TermOf>::term_of(c.clone())))), Box::new(<List<BigInt> as TermOf>::term_of(d.clone())))), Box::new(<A as TermOf>::term_of(e.clone())))
    }
}

impl <A : Clone + Typerep + TermOf + 'static> TermOf for ClassDefExt<A> {
    fn term_of (x0: ClassDefExt<A>) -> Term {
        let ClassDefExt::ClassDefExt (a, b, c, d, e, f) = x0;
        Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::App (Box::new(Term::Const (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))), Box::new(<BigInt as TermOf>::term_of(a.clone())))), Box::new(<BigInt as TermOf>::term_of(b.clone())))), Box::new(<List<VarDefExt<Unit>> as TermOf>::term_of(c.clone())))), Box::new(<ConstructorDefExt<Unit> as TermOf>::term_of(d.clone())))), Box::new(<List<MethodDefExt<Unit>> as TermOf>::term_of(e.clone())))), Box::new(<A as TermOf>::term_of(f.clone())))
    }
}

impl <A : Clone + Typerep + 'static> Typerep for ClassDefExt<A> {
    fn typerep (x0: Itself<ClassDefExt<A>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))
    }
}

impl <A : Clone + Typerep + PartialTermOf + 'static> PartialTermOf for
    ConstructorDefExt<A> {
    fn partial_term_of
        (x0: Itself<ConstructorDefExt<A>>, x1: NarrowingTerm) -> Term {
        match x1 {
            NarrowingTerm::NarrowingVariable (_, _) =>
                Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))),
            NarrowingTerm::NarrowingConstructor (p0, p0a) =>
                panic!("non-exhaustive match"),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl <A : Clone + Typerep + PartialTermOf + 'static> PartialTermOf for
    ClassDefExt<A> {
    fn partial_term_of (x0: Itself<ClassDefExt<A>>, x1: NarrowingTerm) -> Term {
        match x1 {
            NarrowingTerm::NarrowingVariable (_, _) =>
                Term::Free (Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::ZeroLiteral)), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))),
            NarrowingTerm::NarrowingConstructor (p0, p0a) =>
                panic!("non-exhaustive match"),
            _ =>
                panic!("non-exhaustive match")
        }
    }
}

impl <A : Clone + Typerep + Random + 'static> Random for ConstructorDefExt<A> {
    fn random
        (i: Natural,
          eta_arg_0: (Natural, Natural)) -> ((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
        (*scomp(
            (({
                let i_cap = i.clone();
                Rc::new(move |a: (Natural, Natural)| -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                    <BigInt as Random>::random(i_cap.clone(), a.clone())
                })
            }) as Rc<dyn Fn((Natural, Natural)) -> ((BigInt, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
            (({
                let i_cap = i.clone();
                Rc::new(move |x: (BigInt, Rc<dyn Fn(Unit) -> Term>), eta_arg: (Natural, Natural)| -> ((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                    (*scomp(
                        (({
                            let i_capa = i_cap.clone();
                            Rc::new(move |a: (Natural, Natural)| -> ((List<VarDefExt<Unit>>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                                <List<VarDefExt<Unit>> as Random>::random(i_capa.clone(), a.clone())
                            })
                        }) as Rc<dyn Fn((Natural, Natural)) -> ((List<VarDefExt<Unit>>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
                        (({
                            let x_cap = x.clone();
                            let i_capa = i_cap.clone();
                            Rc::new(move |y: (List<VarDefExt<Unit>>, Rc<dyn Fn(Unit) -> Term>), eta_arh: (Natural, Natural)| -> ((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                                (*scomp(
                                    (({
                                        let i_capb = i_capa.clone();
Rc::new(move |a: (Natural, Natural)| -> ((List<BigInt>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
    <List<BigInt> as Random>::random(i_capb.clone(), a.clone())
})
                                    }) as Rc<dyn Fn((Natural, Natural)) -> ((List<BigInt>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
                                    (({
                                        let y_cap = y.clone();
let x_capa = x_cap.clone();
let i_capb = i_capa.clone();
Rc::new(move |z: (List<BigInt>, Rc<dyn Fn(Unit) -> Term>), eta_ari: (Natural, Natural)| -> ((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
    (*scomp(
        (({
            let i_capc = i_capb.clone();
            Rc::new(move |a: (Natural, Natural)| -> ((List<BigInt>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                <List<BigInt> as Random>::random(i_capc.clone(), a.clone())
            })
        }) as Rc<dyn Fn((Natural, Natural)) -> ((List<BigInt>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>),
        (({
            let z_cap = z.clone();
            let y_capa = y_cap.clone();
            let x_capb = x_capa.clone();
            let i_capc = i_capb.clone();
            Rc::new(move |aa: (List<BigInt>, Rc<dyn Fn(Unit) -> Term>), eta_arj: (Natural, Natural)| -> ((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
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
                        Rc::new(move |ab: (A, Rc<dyn Fn(Unit) -> Term>), eta_ark: (Natural, Natural)| -> ((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural)) {
                            (valapp(valapp(valapp(valapp(valapp((
                                ((Rc::new(move |boundary_arg: BigInt| {
                                    (({
                                        let boundary_arg_cap = boundary_arg.clone();
Rc::new(move |boundary_arh: List<VarDefExt<Unit>>| {
    (({
        let boundary_arh_cap = boundary_arh.clone();
        let boundary_arg_capa = boundary_arg_cap.clone();
        Rc::new(move |boundary_ari: List<BigInt>| {
            (({
                let boundary_ari_cap = boundary_ari.clone();
                let boundary_arh_capa = boundary_arh_cap.clone();
                let boundary_arg_capb = boundary_arg_capa.clone();
                Rc::new(move |boundary_arj: List<BigInt>| {
                    (({
                        let boundary_arj_cap = boundary_arj.clone();
                        let boundary_ari_capa = boundary_ari_cap.clone();
                        let boundary_arh_capb = boundary_arh_capa.clone();
                        let boundary_arg_capc = boundary_arg_capb.clone();
                        Rc::new(move |boundary_ark: A| -> ConstructorDefExt<A> {
                            (*{
                                let boundary_ari_capb = boundary_ari_capa.clone();
                                let boundary_arh_capc = boundary_arh_capb.clone();
                                let boundary_arg_capd = boundary_arg_capc.clone();
                                Rc::new(move |boundary_arja: List<BigInt>, boundary_arka: A| {
                                    (*{
                                        let boundary_arh_capd = boundary_arh_capc.clone();
let boundary_arg_cape = boundary_arg_capd.clone();
Rc::new(move |boundary_aria: List<BigInt>, boundary_arjb: List<BigInt>, boundary_arkb: A| {
    (*{
        let boundary_arg_capf = boundary_arg_cape.clone();
        Rc::new(move |boundary_arha: List<VarDefExt<Unit>>, boundary_arib: List<BigInt>, boundary_arjc: List<BigInt>, boundary_arkc: A| {
            ConstructorDefExt::ConstructorDefExt (boundary_arg_capf.clone(), boundary_arha.clone(), boundary_arib.clone(), boundary_arjc.clone(), boundary_arkc.clone())
        })
    })(boundary_arh_capd.clone(), boundary_aria.clone(), boundary_arjb.clone(), boundary_arkb.clone())
})
                                    })(boundary_ari_capb.clone(), boundary_arja.clone(), boundary_arka.clone())
                                })
                            })(boundary_arj_cap.clone(), boundary_ark.clone())
                        })
                    }) as Rc<dyn Fn(A) -> ConstructorDefExt<A>>)
                })
            }) as Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(A) -> ConstructorDefExt<A>>>)
        })
    }) as Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(A) -> ConstructorDefExt<A>>>>)
})
                                    }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(A) -> ConstructorDefExt<A>>>>>)
                                })) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(List<VarDefExt<Unit>>) -> Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(A) -> ConstructorDefExt<A>>>>>>),
                                ((Rc::new(move |_: Unit| -> Term {
                                    Term::Const (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))
                                })) as Rc<dyn Fn(Unit) -> Term>)
                            ), x_capc.clone()), y_capb.clone()), z_capa.clone()), aa_cap.clone()), ab.clone()), eta_ark.clone())
                        })
                    }) as Rc<dyn Fn((A, Rc<dyn Fn(Unit) -> Term>),
                                     (Natural, Natural)) -> ((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
                ))(eta_arj.clone())
            })
        }) as Rc<dyn Fn((List<BigInt>, Rc<dyn Fn(Unit) -> Term>),
                         (Natural, Natural)) -> ((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
    ))(eta_ari.clone())
})
                                    }) as Rc<dyn Fn((List<BigInt>, Rc<dyn Fn(Unit) -> Term>),
             (Natural, Natural)) -> ((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
                                ))(eta_arh.clone())
                            })
                        }) as Rc<dyn Fn((List<VarDefExt<Unit>>, Rc<dyn Fn(Unit) -> Term>),
 (Natural, Natural)) -> ((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
                    ))(eta_arg.clone())
                })
            }) as Rc<dyn Fn((BigInt, Rc<dyn Fn(Unit) -> Term>),
                             (Natural, Natural)) -> ((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>), (Natural, Natural))>)
        ))(eta_arg_0.clone())
    }
}

impl <A : Clone + Typerep + 'static> Typerep for ConstructorDefExt<A> {
    fn typerep (x0: Itself<ConstructorDefExt<A>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))
    }
}

impl <A : Clone + TermOf + Typerep + FullExhaustive + 'static>
    FullExhaustive for ConstructorDefExt<A> {
    fn full_exhaustive
        (f: Rc<dyn Fn((ConstructorDefExt<A>, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>,
          i: Natural) -> Option<(bool, List<Term>)> {
        <BigInt as FullExhaustive>::full_exhaustive(
            (({
                let i_cap = i.clone();
                let f_cap = f.clone();
                Rc::new(move |x: (BigInt, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
                    <List<VarDefExt<Unit>> as FullExhaustive>::full_exhaustive(
                        (({
                            let i_capa = i_cap.clone();
                            let x_cap = x.clone();
                            let f_capa = f_cap.clone();
                            Rc::new(move |y: (List<VarDefExt<Unit>>, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
                                <List<BigInt> as FullExhaustive>::full_exhaustive(
                                    (({
                                        let i_capb = i_capa.clone();
let y_cap = y.clone();
let x_capa = x_cap.clone();
let f_capb = f_capa.clone();
Rc::new(move |z: (List<BigInt>, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
    <List<BigInt> as FullExhaustive>::full_exhaustive(
        (({
            let i_capc = i_capb.clone();
            let z_cap = z.clone();
            let y_capa = y_cap.clone();
            let x_capb = x_capa.clone();
            let f_capc = f_capb.clone();
            Rc::new(move |aa: (List<BigInt>, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
                <A as FullExhaustive>::full_exhaustive(
                    (({
                        let aa_cap = aa.clone();
                        let z_capa = z_cap.clone();
                        let y_capb = y_capa.clone();
                        let x_capc = x_capb.clone();
                        let f_capd = f_capc.clone();
                        Rc::new(move |ab: (A, Rc<dyn Fn(Unit) -> Term>)| -> Option<(bool, List<Term>)> {
                            (*f_capd)(valapp(valapp(valapp(valapp(valapp((
                                ((Rc::new(move |boundary_arg: BigInt| {
                                    (({
                                        let boundary_arg_cap = boundary_arg.clone();
Rc::new(move |boundary_arh: List<VarDefExt<Unit>>| {
    (({
        let boundary_arh_cap = boundary_arh.clone();
        let boundary_arg_capa = boundary_arg_cap.clone();
        Rc::new(move |boundary_ari: List<BigInt>| {
            (({
                let boundary_ari_cap = boundary_ari.clone();
                let boundary_arh_capa = boundary_arh_cap.clone();
                let boundary_arg_capb = boundary_arg_capa.clone();
                Rc::new(move |boundary_arj: List<BigInt>| {
                    (({
                        let boundary_arj_cap = boundary_arj.clone();
                        let boundary_ari_capa = boundary_ari_cap.clone();
                        let boundary_arh_capb = boundary_arh_capa.clone();
                        let boundary_arg_capc = boundary_arg_capb.clone();
                        Rc::new(move |boundary_ark: A| -> ConstructorDefExt<A> {
                            (*{
                                let boundary_ari_capb = boundary_ari_capa.clone();
                                let boundary_arh_capc = boundary_arh_capb.clone();
                                let boundary_arg_capd = boundary_arg_capc.clone();
                                Rc::new(move |boundary_arja: List<BigInt>, boundary_arka: A| {
                                    (*{
                                        let boundary_arh_capd = boundary_arh_capc.clone();
let boundary_arg_cape = boundary_arg_capd.clone();
Rc::new(move |boundary_aria: List<BigInt>, boundary_arjb: List<BigInt>, boundary_arkb: A| {
    (*{
        let boundary_arg_capf = boundary_arg_cape.clone();
        Rc::new(move |boundary_arha: List<VarDefExt<Unit>>, boundary_arib: List<BigInt>, boundary_arjc: List<BigInt>, boundary_arkc: A| {
            ConstructorDefExt::ConstructorDefExt (boundary_arg_capf.clone(), boundary_arha.clone(), boundary_arib.clone(), boundary_arjc.clone(), boundary_arkc.clone())
        })
    })(boundary_arh_capd.clone(), boundary_aria.clone(), boundary_arjb.clone(), boundary_arkb.clone())
})
                                    })(boundary_ari_capb.clone(), boundary_arja.clone(), boundary_arka.clone())
                                })
                            })(boundary_arj_cap.clone(), boundary_ark.clone())
                        })
                    }) as Rc<dyn Fn(A) -> ConstructorDefExt<A>>)
                })
            }) as Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(A) -> ConstructorDefExt<A>>>)
        })
    }) as Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(A) -> ConstructorDefExt<A>>>>)
})
                                    }) as Rc<dyn Fn(List<VarDefExt<Unit>>) -> Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(A) -> ConstructorDefExt<A>>>>>)
                                })) as Rc<dyn Fn(BigInt) -> Rc<dyn Fn(List<VarDefExt<Unit>>) -> Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(List<BigInt>) -> Rc<dyn Fn(A) -> ConstructorDefExt<A>>>>>>),
                                ((Rc::new(move |_: Unit| -> Term {
                                    Term::Const (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (true, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))), Box::new(List::Nil)), Box::new(List::Nil)))), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::ZeroLiteral)))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil)))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))), Box::new(List::Nil)))))))
                                })) as Rc<dyn Fn(Unit) -> Term>)
                            ), x_capc.clone()), y_capb.clone()), z_capa.clone()), aa_cap.clone()), ab.clone()))
                        })
                    }) as Rc<dyn Fn((A, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
                    i_capc.clone()
                )
            })
        }) as Rc<dyn Fn((List<BigInt>, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
        i_capb.clone()
    )
})
                                    }) as Rc<dyn Fn((List<BigInt>, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
                                    i_capa.clone()
                                )
                            })
                        }) as Rc<dyn Fn((List<VarDefExt<Unit>>, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
                        i_cap.clone()
                    )
                })
            }) as Rc<dyn Fn((BigInt, Rc<dyn Fn(Unit) -> Term>)) -> Option<(bool, List<Term>)>>),
            i.clone()
        )
    }
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static, 
       C : Clone + Typerep + 'static>
    Typerep for N2mExpSubstsPreN2mExp<A, B, C> {
    fn typerep (x0: Itself<N2mExpSubstsPreN2mExp<A, B, C>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, true, false, false, false, true, Box::new(Literal::Literal (false, true, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, false, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, false, false, true, true, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Cons (<C as Typerep>::typerep(Itself::Type (PhantomData::<C>)), Box::new(List::Nil))))))))
    }
}
