use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::suc;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::Complete_Lattices::sup_set;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::fold;
use crate::List::list_all2;
use crate::List::mapa;
use crate::List::rev;
use crate::List::size_list;
use crate::Option::Option;
use crate::Option::map_option;
use crate::Orderings::Linorder;
use crate::Orderings::Ord;
use crate::Pure::Itself;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::Quickcheck_Narrowing::PartialTermOf;
use crate::Set::Set;
use crate::Set::image;
use crate::String::Literal;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;

use std::marker::PhantomData;

use std::rc::Rc;

#[derive(Clone)]
pub enum Bintree<A, B> {
    Node (A, B, Box<List<Bintree<A, B>>>)
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static> Typerep for
    Bintree<A, B> {
    fn typerep (x0: Itself<Bintree<A, B>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, false, false, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil))))))
    }
}

#[derive(Clone)]
pub struct
  BintreePreBintree<A, B, C>(PhantomData<A>, PhantomData<B>, PhantomData<C>);

#[derive(Clone)]
pub struct BintreeIITNBintree<A, B>(PhantomData<A>, PhantomData<B>);

pub fn priority <A, B> (x0: Bintree<A, B>) -> A
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        Bintree::Node (a, _, _) =>
            a.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn children <B, A> (x0: Bintree<A, B>) -> List<Bintree<A, B>>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        Bintree::Node (_, _, p0) =>
            {
                let ts = *p0;
                ts.clone()
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn vala <B, A> (x0: Bintree<A, B>) -> B
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        Bintree::Node (_, v, _) =>
            v.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn merge <B, A> (t1: Bintree<A, B>, t2: Bintree<A, B>) -> Bintree<A, B>
where
    A : Clone + Linorder + 'static,
    B : Clone + 'static
{
    if <A as Ord>::less(priority(t1.clone()), priority(t2.clone())) {
        Bintree::Node (priority(t1.clone()), vala(t1.clone()), Box::new(List::Cons (t2.clone(), Box::new(children(t1.clone())))))
    } else {
        Bintree::Node (priority(t2.clone()), vala(t2.clone()), Box::new(List::Cons (t1.clone(), Box::new(children(t2.clone())))))
    }
}

pub fn melda <B, A>
    (z: Option<Bintree<A, B>>, xs: List<Option<Bintree<A, B>>>,
      ys: List<Option<Bintree<A, B>>>) -> List<Option<Bintree<A, B>>>
where
    A : Clone + Linorder + 'static,
    B : Clone + 'static
{
    match (z, xs, ys) {
        (Option::None, List::Nil, ys) =>
            ys.clone(),
        (Option::Some (t), List::Nil, ys) =>
            melda(Option::None, List::Cons (Option::Some (t.clone()), Box::new(List::Nil)), ys.clone()),
        (z, List::Nil, List::Cons (y, p0)) =>
            {
                let ys = *p0;
                melda(Option::None, List::Cons (z.clone(), Box::new(List::Nil)), List::Cons (y.clone(), Box::new(ys.clone())))
            },
        (z, xs, List::Nil) =>
            melda(z.clone(), List::Nil, xs.clone()),
        (z, List::Cons (Option::None, p0), List::Cons (Option::None, p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                List::Cons (z.clone(), Box::new(melda(Option::None, xs.clone(), ys.clone())))
            },
        (Option::None, List::Cons (Option::None, p0), List::Cons (y, p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                List::Cons (y.clone(), Box::new(melda(Option::None, xs.clone(), ys.clone())))
            },
        (Option::None, List::Cons (x, p0), List::Cons (Option::None, p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                List::Cons (x.clone(), Box::new(melda(Option::None, xs.clone(), ys.clone())))
            },
        (Option::Some (t), List::Cons (Option::None, p0), List::Cons (Option::Some (r), p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                List::Cons (Option::None, Box::new(melda(Option::Some (merge(t.clone(), r.clone())), xs.clone(), ys.clone())))
            },
        (Option::Some (t), List::Cons (Option::Some (r), p0), List::Cons (Option::None, p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                List::Cons (Option::None, Box::new(melda(Option::Some (merge(t.clone(), r.clone())), xs.clone(), ys.clone())))
            },
        (z, List::Cons (Option::Some (t), p0), List::Cons (Option::Some (r), p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                List::Cons (z.clone(), Box::new(melda(Option::Some (merge(t.clone(), r.clone())), xs.clone(), ys.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn add <B, A>
    (z: Option<Bintree<A, B>>,
      xs: List<Option<Bintree<A, B>>>) -> List<Option<Bintree<A, B>>>
where
    A : Clone + Linorder + 'static,
    B : Clone + 'static
{
    melda(z.clone(), List::Nil, xs.clone())
}

pub fn least <A> (x: Option<A>, xa: Option<A>) -> Option<A>
where
    A : Clone + Linorder + 'static
{
    match (x, xa) {
        (Option::Some (x), Option::Some (y)) =>
            if <A as Ord>::less_eq(x.clone(), y.clone()) {
                Option::Some (x.clone())
            } else {
                Option::Some (y.clone())
            },
        (x, Option::None) =>
            x.clone(),
        (Option::None, x) =>
            x.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn min <A, B> (xs: List<Option<Bintree<A, B>>>) -> Option<A>
where
    A : Clone + Linorder + 'static,
    B : Clone + 'static
{
    fold(
        ((Rc::new(move |x: Option<Bintree<A,
    B>>, eta_arg: Option<A>| -> Option<A> {
            least(map_option(((Rc::new(move |a: Bintree<A, B>| -> A {
                priority(a.clone())
            })) as Rc<dyn Fn(Bintree<A, B>) -> A>), x.clone()), eta_arg.clone())
        })) as Rc<dyn Fn(Option<Bintree<A, B>>, Option<A>) -> Option<A>>),
        xs.clone(),
        Option::None
    )
}

pub fn normalizea <B, A>
    (x0: List<Option<Bintree<A, B>>>) -> List<Option<Bintree<A, B>>>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        List::Nil =>
            List::Nil,
        List::Cons (x, p0) =>
            {
                let xs = *p0;
                match x.clone() {
                    Option::None =>
                        normalizea(xs.clone()),
                    Option::Some (_) =>
                        List::Cons (x.clone(), Box::new(xs.clone())),
                    _ =>
                        panic!("non-exhaustive match")
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn normalize <B, A>
    (xs: List<Option<Bintree<A, B>>>) -> List<Option<Bintree<A, B>>>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    rev(normalizea(rev(xs.clone())))
}

pub fn find <B, A>
    (a: A, x1: List<Option<Bintree<A, B>>>) -> Option<Bintree<A, B>>
where
    A : Clone + Equal + Linorder + 'static,
    B : Clone + 'static
{
    match (a, x1) {
        (a, List::Cons (Option::Some (t), p0)) =>
            {
                let xs = *p0;
                if eq(priority(t.clone()), a.clone()) {
                    Option::Some (t.clone())
                } else {
                    find(a.clone(), xs.clone())
                }
            },
        (a, List::Cons (Option::None, p0)) =>
            {
                let xs = *p0;
                find(a.clone(), xs.clone())
            },
        (_, List::Nil) =>
            Option::None,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn find_min <B, A>
    (xs: List<Option<Bintree<A, B>>>) -> Option<Bintree<A, B>>
where
    A : Clone + Equal + Linorder + 'static,
    B : Clone + 'static
{
    match min(xs.clone()) {
        Option::None =>
            Option::None,
        Option::Some (a) =>
            find(a.clone(), xs.clone()),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn matcha <B, A> (a: A, x1: Option<Bintree<A, B>>) -> Option<Bintree<A, B>>
where
    A : Clone + Equal + Linorder + 'static,
    B : Clone + 'static
{
    match (a, x1) {
        (_, Option::None) =>
            Option::None,
        (a, Option::Some (t)) =>
            if eq(priority(t.clone()), a.clone()) {
                Option::None
            } else {
                Option::Some (t.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn meld <B, A>
    (xs: List<Option<Bintree<A, B>>>,
      ys: List<Option<Bintree<A, B>>>) -> List<Option<Bintree<A, B>>>
where
    A : Clone + Linorder + 'static,
    B : Clone + 'static
{
    melda(Option::None, xs.clone(), ys.clone())
}

pub fn pop <B, A>
    (xs: List<Option<Bintree<A, B>>>) -> (Option<(B, A)>, List<Option<Bintree<A,
B>>>)
where
    A : Clone + Equal + Linorder + 'static,
    B : Clone + 'static
{
    match find_min(xs.clone()) {
        Option::None =>
            (Option::None, xs.clone()),
        Option::Some (t) =>
            (Option::Some ((vala(t.clone()), priority(t.clone()))), normalize(meld(mapa(((Rc::new(move |a: Bintree<A,
                                     B>| -> Option<Bintree<A, B>> {
                Option::Some (a.clone())
            })) as Rc<dyn Fn(Bintree<A, B>) -> Option<Bintree<A,
                        B>>>), rev(children(t.clone()))), mapa((({
                let t_cap = t.clone();
                Rc::new(move |a: Option<Bintree<A,
          B>>| -> Option<Bintree<A, B>> {
                    matcha(priority(t_cap.clone()), a.clone())
                })
            }) as Rc<dyn Fn(Option<Bintree<A,
     B>>) -> Option<Bintree<A, B>>>), xs.clone())))),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn insert <B, A>
    (a: A, v: B, xs: List<Option<Bintree<A, B>>>) -> List<Option<Bintree<A, B>>>
where
    A : Clone + Linorder + 'static,
    B : Clone + 'static
{
    add(Option::Some (Bintree::Node (a.clone(), v.clone(), Box::new(List::Nil))), xs.clone())
}

pub fn delete_min <B, A>
    (xs: List<Option<Bintree<A, B>>>) -> List<Option<Bintree<A, B>>>
where
    A : Clone + Equal + Linorder + 'static,
    B : Clone + 'static
{
    match find_min(xs.clone()) {
        Option::None =>
            List::Nil,
        Option::Some (Bintree::Node (a, _, p0)) =>
            {
                let ts = *p0;
                normalize(meld(mapa(((Rc::new(move |aa: Bintree<A,
                          B>| -> Option<Bintree<A, B>> {
                    Option::Some (aa.clone())
                })) as Rc<dyn Fn(Bintree<A,
   B>) -> Option<Bintree<A, B>>>), rev(ts.clone())), mapa((({
                    let a_cap = a.clone();
                    Rc::new(move |b: Option<Bintree<A,
              B>>| -> Option<Bintree<A, B>> {
                        matcha(a_cap.clone(), b.clone())
                    })
                }) as Rc<dyn Fn(Option<Bintree<A,
         B>>) -> Option<Bintree<A, B>>>), xs.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn map_bintree <D, B, C, A>
    (f1: Rc<dyn Fn(A) -> B>, f2: Rc<dyn Fn(C) -> D>,
      x2: Bintree<A, C>) -> Bintree<B, D>
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static,
    D : Clone + 'static
{
    match (f1, f2, x2) {
        (f1, f2, Bintree::Node (x1, x2, p0)) =>
            {
                let x3 = *p0;
                Bintree::Node ((*f1)(x1.clone()), (*f2)(x2.clone()), Box::new(mapa((({
                                   let f2_cap = f2.clone();
                                   let f1_cap = f1.clone();
                                   Rc::new(move |a: Bintree<A,
                      C>| -> Bintree<B, D> {
                                       map_bintree(f1_cap.clone(), f2_cap.clone(), a.clone())
                                   })
                               }) as Rc<dyn Fn(Bintree<A,
                 C>) -> Bintree<B, D>>), x3.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rec_bintree <C, B, A>
    (f: Rc<dyn Fn(A, B, List<(Bintree<A, B>, C)>) -> C>, x1: Bintree<A, B>) -> C
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static
{
    match (f, x1) {
        (f, Bintree::Node (x1, x2, p0)) =>
            {
                let x3 = *p0;
                (*f)(x1.clone(), x2.clone(), mapa(
                    (({
                        let f_cap = f.clone();
                        Rc::new(move |bintree: Bintree<A,
                 B>| -> (Bintree<A, B>, C) {
                            (bintree.clone(), rec_bintree(f_cap.clone(), bintree.clone()))
                        })
                    }) as Rc<dyn Fn(Bintree<A, B>) -> (Bintree<A, B>, C)>),
                    x3.clone()
                ))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rel_bintree <D, B, C, A>
    (r1: Rc<dyn Fn(A, B) -> bool>, r2: Rc<dyn Fn(C, D) -> bool>,
      x2: Bintree<A, C>, x3: Bintree<B, D>) -> bool
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static,
    D : Clone + 'static
{
    match (r1, r2, x2, x3) {
        (r1, r2, Bintree::Node (x1, x2, p0), Bintree::Node (y1, y2, p1)) =>
            {
                let x3 = *p0;
                let y3 = *p1;
                (*r1)(x1.clone(), y1.clone()) &&
                  ((*r2)(x2.clone(), y2.clone()) &&
                    list_all2((({
                        let r2_cap = r2.clone();
                        let r1_cap = r1.clone();
                        Rc::new(move |a: Bintree<A,
           C>, b: Bintree<B, D>| -> bool {
                            rel_bintree(r1_cap.clone(), r2_cap.clone(), a.clone(), b.clone())
                        })
                    }) as Rc<dyn Fn(Bintree<A, C>,
                                     Bintree<B,
       D>) -> bool>), x3.clone(), y3.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn set1_bintree <A, B> (x0: Bintree<A, B>) -> Set<A>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match x0 {
        Bintree::Node (x1, _, p0) =>
            {
                let x3 = *p0;
                crate::Set::insert(x1.clone(), sup_set(image(((Rc::new(move |a: Bintree<A,
          B>| -> Set<A> {
                    set1_bintree(a.clone())
                })) as Rc<dyn Fn(Bintree<A,
   B>) -> Set<A>>), Set::Set (x3.clone()))))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn set2_bintree <B, A> (x0: Bintree<A, B>) -> Set<B>
where
    A : Clone + 'static,
    B : Clone + Equal + 'static
{
    match x0 {
        Bintree::Node (_, x2, p0) =>
            {
                let x3 = *p0;
                crate::Set::insert(x2.clone(), sup_set(image(((Rc::new(move |a: Bintree<A,
          B>| -> Set<B> {
                    set2_bintree(a.clone())
                })) as Rc<dyn Fn(Bintree<A,
   B>) -> Set<B>>), Set::Set (x3.clone()))))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_bintree <B, A>
    (xa: Rc<dyn Fn(A) -> BigInt>, x: Rc<dyn Fn(B) -> BigInt>,
      xb2: Bintree<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (xa, x, xb2) {
        (xa, x, Bintree::Node (x1, x2, p0)) =>
            {
                let x3 = *p0;
                (*xa)(x1.clone()) + (*x)(x2.clone()) +
                  size_list((({
                      let x_cap = x.clone();
                      let xa_cap = xa.clone();
                      Rc::new(move |a: Bintree<A, B>| -> BigInt {
                          size_bintree(xa_cap.clone(), x_cap.clone(), a.clone())
                      })
                  }) as Rc<dyn Fn(Bintree<A, B>) -> BigInt>), x3.clone()) +
                  suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_bintreea <B, A> (x0: Bintree<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        Bintree::Node (_, _, p0) =>
            {
                let x3 = *p0;
                size_list(((Rc::new(move |a: Bintree<A, B>| -> BigInt {
                      size_bintreea(a.clone())
                  })) as Rc<dyn Fn(Bintree<A, B>) -> BigInt>), x3.clone()) +
                  suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static, 
       C : Clone + Typerep + 'static>
    Typerep for BintreePreBintree<A, B, C> {
    fn typerep (x0: Itself<BintreePreBintree<A, B, C>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, false, false, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Cons (<C as Typerep>::typerep(Itself::Type (PhantomData::<C>)), Box::new(List::Nil))))))))
    }
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static> Typerep for
    BintreeIITNBintree<A, B> {
    fn typerep (x0: Itself<BintreeIITNBintree<A, B>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, true, false, false, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, false, true, true, Box::new(Literal::Literal (true, false, true, true, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, false, false, true, false, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, true, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil))))))
    }
}
