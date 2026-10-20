use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Plus;
use crate::Arith::Zero;
use crate::Arith::suc;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::Complete_Lattices::sup_set;
use crate::Groups_List::sum_list;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::list_all;
use crate::List::list_all2;
use crate::List::mapa;
use crate::List::size_list;
use crate::Multiset::Multiset;
use crate::Multiset::add_mset;
use crate::Multiset::set_mset;
use crate::Option::Option;
use crate::Orderings::Linorder;
use crate::Orderings::Ord;
use crate::Pure::Itself;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::Quickcheck_Narrowing::PartialTermOf;
use crate::Set::Set;
use crate::Set::ball;
use crate::Set::image;
use crate::String::Literal;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;

use std::marker::PhantomData;

use std::rc::Rc;

#[derive(Clone)]
pub enum Hp<A> {
    Hp (A, Box<List<Hp<A>>>)
}

impl <A : Clone + Typerep + 'static> Typerep for Hp<A> {
    fn typerep (x0: Itself<Hp<A>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))
    }
}

#[derive(Clone)]
pub struct HpIITNHp<A>(PhantomData<A>);

pub fn mset_hp <A> (x0: Hp<A>) -> Multiset<A>
where
    A : Clone + 'static
{
    match x0 {
        Hp::Hp (x, p0) =>
            {
                let hs = *p0;
                <Multiset<A> as Plus>::plus(add_mset(x.clone(), <Multiset<A> as Zero>::zero()), sum_list(mapa(((Rc::new(move |a: Hp<A>| -> Multiset<A> {
                    mset_hp(a.clone())
                })) as Rc<dyn Fn(Hp<A>) -> Multiset<A>>), hs.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn php <A> (x0: Hp<A>) -> bool
where
    A : Clone + Linorder + 'static
{
    match x0 {
        Hp::Hp (x, p0) =>
            {
                let hs = *p0;
                list_all(
                    (({
                        let x_cap = x.clone();
                        Rc::new(move |h: Hp<A>| -> bool {
                            ball(set_mset(mset_hp(h.clone())), (({
                                  let x_capa = x_cap.clone();
                                  Rc::new(move |a: A| -> bool {
                                      <A as Ord>::less_eq(x_capa.clone(), a.clone())
                                  })
                              }) as Rc<dyn Fn(A) -> bool>)) && php(h.clone())
                        })
                    }) as Rc<dyn Fn(Hp<A>) -> bool>),
                    hs.clone()
                )
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn link <A> (x0: Hp<A>, x1: Hp<A>) -> Hp<A>
where
    A : Clone + Linorder + 'static
{
    match (x0, x1) {
        (Hp::Hp (x1, p0), Hp::Hp (x2, p1)) =>
            {
                let hs1 = *p0;
                let hs2 = *p1;
                if <A as Ord>::less(x1.clone(), x2.clone()) {
                    Hp::Hp (x1.clone(), Box::new(List::Cons (Hp::Hp (x2.clone(), Box::new(hs2.clone())), Box::new(hs1.clone()))))
                } else {
                    Hp::Hp (x2.clone(), Box::new(List::Cons (Hp::Hp (x1.clone(), Box::new(hs1.clone())), Box::new(hs2.clone()))))
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn invar <A> (ho: Option<Hp<A>>) -> bool
where
    A : Clone + Linorder + 'static
{
    match ho.clone() {
        Option::None =>
            true,
        Option::Some (a) =>
            php(a.clone()),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn merge <A> (ho: Option<Hp<A>>, x1: Option<Hp<A>>) -> Option<Hp<A>>
where
    A : Clone + Linorder + 'static
{
    match (ho, x1) {
        (ho, Option::None) =>
            ho.clone(),
        (Option::None, Option::Some (v)) =>
            Option::Some (v.clone()),
        (Option::Some (h1), Option::Some (h2)) =>
            Option::Some (link(h1.clone(), h2.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn hps <A> (x0: Hp<A>) -> List<Hp<A>>
where
    A : Clone + 'static
{
    match x0 {
        Hp::Hp (_, p0) =>
            {
                let x2 = *p0;
                x2.clone()
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn insert <A> (x: A, xa1: Option<Hp<A>>) -> Option<Hp<A>>
where
    A : Clone + Linorder + 'static
{
    match (x, xa1) {
        (x, Option::None) =>
            Option::Some (Hp::Hp (x.clone(), Box::new(List::Nil))),
        (x, Option::Some (h)) =>
            Option::Some (link(Hp::Hp (x.clone(), Box::new(List::Nil)), h.clone())),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn merge_pairs <A> (x0: List<Hp<A>>) -> Option<Hp<A>>
where
    A : Clone + Linorder + 'static
{
    match x0 {
        List::Nil =>
            Option::None,
        List::Cons (p0, p0a) =>
            match *p0a {
                List::Nil =>
                    {
                        let h = p0;
                        Option::Some (h.clone())
                    },
                List::Cons (h2, p1a) =>
                    {
                        let h1 = p0;
                        let hs = *p1a;
                        Option::Some (
                            {
                                let h12 = link(h1.clone(), h2.clone());
                                match merge_pairs(hs.clone()) {
                                    Option::None =>
                                        h12.clone(),
                                    Option::Some (a) =>
                                        link(h12.clone(), a.clone()),
                                    _ =>
                                        panic!("non-exhaustive match")
                                }
                            }
                        )
                    },
                _ =>
                    panic!("non-exhaustive match")
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn del_min <A> (x0: Option<Hp<A>>) -> Option<Hp<A>>
where
    A : Clone + Linorder + 'static
{
    match x0 {
        Option::None =>
            Option::None,
        Option::Some (Hp::Hp (_, p0)) =>
            {
                let hs = *p0;
                merge_pairs(hs.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn get_min <A> (x0: Option<Hp<A>>) -> A
where
    A : Clone + 'static
{
    match x0 {
        Option::Some (Hp::Hp (x, _)) =>
            x.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn map_hp <B, A> (f: Rc<dyn Fn(A) -> B>, x1: Hp<A>) -> Hp<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (f, Hp::Hp (x1, p0)) =>
            {
                let x2 = *p0;
                Hp::Hp ((*f)(x1.clone()), Box::new(mapa((({
        let f_cap = f.clone();
        Rc::new(move |a: Hp<A>| -> Hp<B> {
            map_hp(f_cap.clone(), a.clone())
        })
    }) as Rc<dyn Fn(Hp<A>) -> Hp<B>>), x2.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rec_hp <B, A> (f: Rc<dyn Fn(A, List<(Hp<A>, B)>) -> B>, x1: Hp<A>) -> B
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (f, Hp::Hp (x1, p0)) =>
            {
                let x2 = *p0;
                (*f)(x1.clone(), mapa(
                    (({
                        let f_cap = f.clone();
                        Rc::new(move |hp: Hp<A>| -> (Hp<A>, B) {
                            (hp.clone(), rec_hp(f_cap.clone(), hp.clone()))
                        })
                    }) as Rc<dyn Fn(Hp<A>) -> (Hp<A>, B)>),
                    x2.clone()
                ))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rel_hp <B, A> (r: Rc<dyn Fn(A, B) -> bool>, x1: Hp<A>, x2: Hp<B>) -> bool
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (r, x1, x2) {
        (r, Hp::Hp (x1, p0), Hp::Hp (y1, p1)) =>
            {
                let x2 = *p0;
                let y2 = *p1;
                (*r)(x1.clone(), y1.clone()) &&
                  list_all2((({
                      let r_cap = r.clone();
                      Rc::new(move |a: Hp<A>, b: Hp<B>| -> bool {
                          rel_hp(r_cap.clone(), a.clone(), b.clone())
                      })
                  }) as Rc<dyn Fn(Hp<A>,
                                   Hp<B>) -> bool>), x2.clone(), y2.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn set_hp <A> (x0: Hp<A>) -> Set<A>
where
    A : Clone + Equal + 'static
{
    match x0 {
        Hp::Hp (x1, p0) =>
            {
                let x2 = *p0;
                crate::Set::insert(x1.clone(), sup_set(image(((Rc::new(move |a: Hp<A>| -> Set<A> {
                    set_hp(a.clone())
                })) as Rc<dyn Fn(Hp<A>) -> Set<A>>), Set::Set (x2.clone()))))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn un__hp1 <A> (x0: Hp<A>) -> A
where
    A : Clone + 'static
{
    match x0 {
        Hp::Hp (x1, _) =>
            x1.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn mset_heap <A> (ho: Option<Hp<A>>) -> Multiset<A>
where
    A : Clone + 'static
{
    match ho.clone() {
        Option::None =>
            <Multiset<A> as Zero>::zero(),
        Option::Some (a) =>
            mset_hp(a.clone()),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_hp <A> (x: Rc<dyn Fn(A) -> BigInt>, xa1: Hp<A>) -> BigInt
where
    A : Clone + 'static
{
    match (x, xa1) {
        (x, Hp::Hp (x1, p0)) =>
            {
                let x2 = *p0;
                (*x)(x1.clone()) +
                  size_list((({
                      let x_cap = x.clone();
                      Rc::new(move |a: Hp<A>| -> BigInt {
                          size_hp(x_cap.clone(), a.clone())
                      })
                  }) as Rc<dyn Fn(Hp<A>) -> BigInt>), x2.clone()) +
                  suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn pass_1 <A> (x0: List<Hp<A>>) -> List<Hp<A>>
where
    A : Clone + Linorder + 'static
{
    match x0 {
        List::Cons (p0, p0a) =>
            match *p0a {
                List::Cons (h2, p1a) =>
                    {
                        let h1 = p0;
                        let hs = *p1a;
                        List::Cons (link(h1.clone(), h2.clone()), Box::new(pass_1(hs.clone())))
                    },
                List::Nil =>
                    {
                        let v = p0;
                        List::Cons (v.clone(), Box::new(List::Nil))
                    },
                _ =>
                    panic!("non-exhaustive match")
            },
        List::Nil =>
            List::Nil,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn pass_2 <A> (x0: List<Hp<A>>) -> Option<Hp<A>>
where
    A : Clone + Linorder + 'static
{
    match x0 {
        List::Nil =>
            Option::None,
        List::Cons (h, p0) =>
            {
                let hs = *p0;
                Option::Some (
                    match pass_2(hs.clone()) {
                        Option::None =>
                            h.clone(),
                        Option::Some (a) =>
                            link(h.clone(), a.clone()),
                        _ =>
                            panic!("non-exhaustive match")
                    }
                )
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_hpa <A> (x0: Hp<A>) -> BigInt
where
    A : Clone + 'static
{
    match x0 {
        Hp::Hp (_, p0) =>
            {
                let x2 = *p0;
                size_list(((Rc::new(move |a: Hp<A>| -> BigInt {
                      size_hpa(a.clone())
                  })) as Rc<dyn Fn(Hp<A>) -> BigInt>), x2.clone()) +
                  suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

impl <A : Clone + Typerep + 'static> Typerep for HpIITNHp<A> {
    fn typerep (x0: Itself<HpIITNHp<A>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))
    }
}
