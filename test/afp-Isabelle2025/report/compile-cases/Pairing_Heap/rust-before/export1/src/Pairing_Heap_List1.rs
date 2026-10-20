use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::Plus;
use crate::Arith::Zero;
use crate::Arith::suc;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::Complete_Lattices::sup_set;
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
use crate::Multiset::sum_mset;
use crate::Orderings::Linorder;
use crate::Orderings::Ord;
use crate::Pure::Itself;
use crate::Quickcheck_Narrowing::NarrowingTerm;
use crate::Quickcheck_Narrowing::NarrowingType;
use crate::Quickcheck_Narrowing::PartialTermOf;
use crate::Set::Set;
use crate::Set::ball;
use crate::Set::bot_set;
use crate::Set::image;
use crate::String::Literal;
use crate::Typerep::Typerep;
use crate::Typerep::Typerepa;

use std::marker::PhantomData;

use std::rc::Rc;

#[derive(Clone)]
pub enum Heap<A> {
    Empty,
    Hp (A, Box<List<Heap<A>>>)
}

impl <A : Clone + Typerep + 'static> Typerep for Heap<A> {
    fn typerep (x0: Itself<Heap<A>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, true, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))
    }
}

#[derive(Clone)]
pub struct HeapPreHeap<A, B>(PhantomData<A>, PhantomData<B>);

#[derive(Clone)]
pub struct HeapIITNHeap<A>(PhantomData<A>);

pub fn merge <A> (h: Heap<A>, x1: Heap<A>) -> Heap<A>
where
    A : Clone + Linorder + 'static
{
    match (h, x1) {
        (h, Heap::Empty) =>
            h.clone(),
        (Heap::Empty, Heap::Hp (v, p0)) =>
            {
                let va = *p0;
                Heap::Hp (v.clone(), Box::new(va.clone()))
            },
        (Heap::Hp (x, p0), Heap::Hp (y, p1)) =>
            {
                let hsx = *p0;
                let hsy = *p1;
                {
                    let hy = Heap::Hp (y.clone(), Box::new(hsy.clone()));
                    let hx = Heap::Hp (x.clone(), Box::new(hsx.clone()));
                    if <A as Ord>::less(x.clone(), y.clone()) {
                        Heap::Hp (x.clone(), Box::new(List::Cons (hy.clone(), Box::new(hsx.clone()))))
                    } else {
                        Heap::Hp (y.clone(), Box::new(List::Cons (hx.clone(), Box::new(hsy.clone()))))
                    }
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn mset_heap <A> (x0: Heap<A>) -> Multiset<A>
where
    A : Clone + 'static
{
    match x0 {
        Heap::Empty =>
            <Multiset<A> as Zero>::zero(),
        Heap::Hp (x, p0) =>
            {
                let hs = *p0;
                <Multiset<A> as Plus>::plus(add_mset(x.clone(), <Multiset<A> as Zero>::zero()), sum_mset(Multiset::Mset (mapa(((Rc::new(move |a: Heap<A>| -> Multiset<A> {
                    mset_heap(a.clone())
                })) as Rc<dyn Fn(Heap<A>) -> Multiset<A>>), hs.clone()))))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn pheap <A> (x0: Heap<A>) -> bool
where
    A : Clone + Linorder + 'static
{
    match x0 {
        Heap::Empty =>
            true,
        Heap::Hp (x, p0) =>
            {
                let hs = *p0;
                list_all(
                    (({
                        let x_cap = x.clone();
                        Rc::new(move |h: Heap<A>| -> bool {
                            ball(set_mset(mset_heap(h.clone())), (({
                                  let x_capa = x_cap.clone();
                                  Rc::new(move |a: A| -> bool {
                                      <A as Ord>::less_eq(x_capa.clone(), a.clone())
                                  })
                              }) as Rc<dyn Fn(A) -> bool>)) && pheap(h.clone())
                        })
                    }) as Rc<dyn Fn(Heap<A>) -> bool>),
                    hs.clone()
                )
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn insert <A> (x: A, h: Heap<A>) -> Heap<A>
where
    A : Clone + Linorder + 'static
{
    merge(Heap::Hp (x.clone(), Box::new(List::Nil)), h.clone())
}

pub fn merge_pairs <A> (x0: List<Heap<A>>) -> Heap<A>
where
    A : Clone + Linorder + 'static
{
    match x0 {
        List::Nil =>
            Heap::Empty,
        List::Cons (p0, p0a) =>
            match *p0a {
                List::Nil =>
                    {
                        let h = p0;
                        h.clone()
                    },
                List::Cons (h2, p1a) =>
                    {
                        let h1 = p0;
                        let hs = *p1a;
                        merge(merge(h1.clone(), h2.clone()), merge_pairs(hs.clone()))
                    },
                _ =>
                    panic!("non-exhaustive match")
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn del_min <A> (x0: Heap<A>) -> Heap<A>
where
    A : Clone + Linorder + 'static
{
    match x0 {
        Heap::Empty =>
            Heap::Empty,
        Heap::Hp (_, p0) =>
            {
                let hs = *p0;
                merge_pairs(hs.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn get_min <A> (x0: Heap<A>) -> A
where
    A : Clone + 'static
{
    match x0 {
        Heap::Hp (x, _) =>
            x.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn pass_1 <A> (x0: List<Heap<A>>) -> List<Heap<A>>
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
                        List::Cons (merge(h1.clone(), h2.clone()), Box::new(pass_1(hs.clone())))
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

pub fn pass_2 <A> (x0: List<Heap<A>>) -> Heap<A>
where
    A : Clone + Linorder + 'static
{
    match x0 {
        List::Nil =>
            Heap::Empty,
        List::Cons (h, p0) =>
            {
                let hs = *p0;
                merge(h.clone(), pass_2(hs.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn map_heap <B, A> (f: Rc<dyn Fn(A) -> B>, x1: Heap<A>) -> Heap<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (_, Heap::Empty) =>
            Heap::Empty,
        (f, Heap::Hp (x21, p0)) =>
            {
                let x22 = *p0;
                Heap::Hp ((*f)(x21.clone()), Box::new(mapa((({
           let f_cap = f.clone();
           Rc::new(move |a: Heap<A>| -> Heap<B> {
               map_heap(f_cap.clone(), a.clone())
           })
       }) as Rc<dyn Fn(Heap<A>) -> Heap<B>>), x22.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rec_heap <A, B>
    (f1: A, f2: Rc<dyn Fn(B, List<(Heap<B>, A)>) -> A>, x2: Heap<B>) -> A
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f1, f2, x2) {
        (f1, _, Heap::Empty) =>
            f1.clone(),
        (f1, f2, Heap::Hp (x21, p0)) =>
            {
                let x22 = *p0;
                (*f2)(x21.clone(), mapa(
                    (({
                        let f2_cap = f2.clone();
                        let f1_cap = f1.clone();
                        Rc::new(move |heap: Heap<B>| -> (Heap<B>, A) {
                            (heap.clone(), rec_heap(f1_cap.clone(), f2_cap.clone(), heap.clone()))
                        })
                    }) as Rc<dyn Fn(Heap<B>) -> (Heap<B>, A)>),
                    x22.clone()
                ))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rel_heap <B, A>
    (r: Rc<dyn Fn(A, B) -> bool>, x1: Heap<A>, x2: Heap<B>) -> bool
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (r, x1, x2) {
        (_, Heap::Empty, Heap::Hp (_, _)) =>
            false,
        (_, Heap::Hp (_, _), Heap::Empty) =>
            false,
        (_, Heap::Empty, Heap::Empty) =>
            true,
        (r, Heap::Hp (x21, p0), Heap::Hp (y21, p1)) =>
            {
                let x22 = *p0;
                let y22 = *p1;
                (*r)(x21.clone(), y21.clone()) &&
                  list_all2((({
                      let r_cap = r.clone();
                      Rc::new(move |a: Heap<A>, b: Heap<B>| -> bool {
                          rel_heap(r_cap.clone(), a.clone(), b.clone())
                      })
                  }) as Rc<dyn Fn(Heap<A>,
                                   Heap<B>) -> bool>), x22.clone(), y22.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn set_heap <A> (x0: Heap<A>) -> Set<A>
where
    A : Clone + Equal + 'static
{
    match x0 {
        Heap::Empty =>
            bot_set::<A>(),
        Heap::Hp (x21, p0) =>
            {
                let x22 = *p0;
                crate::Set::insert(x21.clone(), sup_set(image(((Rc::new(move |a: Heap<A>| -> Set<A> {
                    set_heap(a.clone())
                })) as Rc<dyn Fn(Heap<A>) -> Set<A>>), Set::Set (x22.clone()))))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_heap <A> (x: Rc<dyn Fn(A) -> BigInt>, xa1: Heap<A>) -> BigInt
where
    A : Clone + 'static
{
    match (x, xa1) {
        (_, Heap::Empty) =>
            BigInt::ZERO,
        (x, Heap::Hp (x21, p0)) =>
            {
                let x22 = *p0;
                (*x)(x21.clone()) +
                  size_list((({
                      let x_cap = x.clone();
                      Rc::new(move |a: Heap<A>| -> BigInt {
                          size_heap(x_cap.clone(), a.clone())
                      })
                  }) as Rc<dyn Fn(Heap<A>) -> BigInt>), x22.clone()) +
                  suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_heapa <A> (x0: Heap<A>) -> BigInt
where
    A : Clone + 'static
{
    match x0 {
        Heap::Empty =>
            BigInt::ZERO,
        Heap::Hp (_, p0) =>
            {
                let x22 = *p0;
                size_list(((Rc::new(move |a: Heap<A>| -> BigInt {
                      size_heapa(a.clone())
                  })) as Rc<dyn Fn(Heap<A>) -> BigInt>), x22.clone()) +
                  suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static> Typerep for
    HeapPreHeap<A, B> {
    fn typerep (x0: Itself<HeapPreHeap<A, B>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, true, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil))))))
    }
}

impl <A : Clone + Typerep + 'static> Typerep for HeapIITNHeap<A> {
    fn typerep (x0: Itself<HeapIITNHeap<A>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, false, false, false, true, false, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, true, Box::new(Literal::Literal (true, true, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, true, false, false, true, true, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (true, false, false, false, true, true, false, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, false, false, false, false, true, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Nil))))
    }
}
