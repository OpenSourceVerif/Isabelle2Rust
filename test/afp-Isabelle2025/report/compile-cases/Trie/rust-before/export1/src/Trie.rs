use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::AList::delete_aux;
use crate::AList::update;
use crate::AList::update_with_aux;
use crate::Arith::suc;
use crate::Basic_BNF_LFPs::size_prod;
use crate::Basic_BNFs::fsts;
use crate::Basic_BNFs::rel_prod;
use crate::Basic_BNFs::snds;
use crate::Code_Evaluation::Term;
use crate::Code_Evaluation::TermOf;
use crate::Fun::id;
use crate::HOL::Equal;
use crate::List::List;
use crate::List::distinct;
use crate::List::list_all;
use crate::List::list_all2;
use crate::List::mapa;
use crate::List::null;
use crate::List::size_list;
use crate::Map::map_of;
use crate::Option::Option;
use crate::Option::is_none;
use crate::Option::map_option;
use crate::Option::rel_option;
use crate::Option::set_option;
use crate::Option::size_option;
use crate::Option::size_optiona;
use crate::Product_Type::fst;
use crate::Product_Type::map_prod;
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
pub enum Trie<A, B> {
    Trie (Option<B>, Box<List<(A, Trie<A, B>)>>)
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static> Typerep for
    Trie<A, B> {
    fn typerep (x0: Itself<Trie<A, B>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil))))))
    }
}

#[derive(Clone)]
pub struct TriePreTrie<A, B, C>(PhantomData<A>, PhantomData<B>, PhantomData<C>);

#[derive(Clone)]
pub struct TrieIITNTrie<A, B>(PhantomData<A>, PhantomData<B>);

pub fn all_trie <A, B> (p: Rc<dyn Fn(A) -> bool>, x1: Trie<B, A>) -> bool
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (p, x1) {
        (p, Trie::Trie (v, p0)) =>
            {
                let ps = *p0;
                match v.clone() {
                      Option::None =>
                          true,
                      Option::Some (a) =>
                          (*p)(a.clone()),
                      _ =>
                          panic!("non-exhaustive match")
                  } &&
                  list_all(
                      (({
                          let p_cap = p.clone();
                          Rc::new(move |(_, a): (B, Trie<B, A>)| -> bool {
                              all_trie(p_cap.clone(), a.clone())
                          })
                      }) as Rc<dyn Fn((B, Trie<B, A>)) -> bool>),
                      ps.clone()
                  )
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn empty_trie <B, A> () -> Trie<A, B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    Trie::Trie (Option::None, Box::new(List::Nil))
}

pub fn is_empty_trie <B, A> (x0: Trie<A, B>) -> bool
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        Trie::Trie (v, p0) =>
            {
                let m = *p0;
                is_none(v.clone()) && null(m.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn invar_trie <B, A> (x0: Trie<A, B>) -> bool
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match x0 {
        Trie::Trie (_, p0) =>
            {
                let kts = *p0;
                distinct(mapa(((Rc::new(move |a: (A, Trie<A, B>)| -> A {
                      fst(a.clone())
                  })) as Rc<dyn Fn((A, Trie<A, B>)) -> A>), kts.clone())) &&
                  list_all(
                      ((Rc::new(move |(_, t): (A, Trie<A, B>)| -> bool {
                          ! is_empty_trie(t.clone()) && invar_trie(t.clone())
                      })) as Rc<dyn Fn((A, Trie<A, B>)) -> bool>),
                      kts.clone()
                  )
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn delete_trie <B, A> (x0: List<A>, x1: Trie<A, B>) -> Trie<A, B>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match (x0, x1) {
        (List::Nil, Trie::Trie (_, p0)) =>
            {
                let ts = *p0;
                Trie::Trie (Option::None, Box::new(ts.clone()))
            },
        (List::Cons (k, p0), Trie::Trie (vo, p1)) =>
            {
                let ks = *p0;
                let ts = *p1;
                match map_of(ts.clone(), k.clone()) {
                    Option::None =>
                        Trie::Trie (vo.clone(), Box::new(ts.clone())),
                    Option::Some (t) =>
                        {
                            let ta = delete_trie(ks.clone(), t.clone());
                            if is_empty_trie(ta.clone()) {
                                Trie::Trie (vo.clone(), Box::new(delete_aux(k.clone(), ts.clone())))
                            } else {
                                Trie::Trie (vo.clone(), Box::new(update(k.clone(), ta.clone(), ts.clone())))
                            }
                        },
                    _ =>
                        panic!("non-exhaustive match")
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn lookup_trie <B, A> (x0: Trie<A, B>, x1: List<A>) -> Option<B>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match (x0, x1) {
        (Trie::Trie (v, _), List::Nil) =>
            v.clone(),
        (Trie::Trie (_, p0), List::Cons (k, p1)) =>
            {
                let m = *p0;
                let ks = *p1;
                match map_of(m.clone(), k.clone()) {
                    Option::None =>
                        Option::None,
                    Option::Some (st) =>
                        lookup_trie(st.clone(), ks.clone()),
                    _ =>
                        panic!("non-exhaustive match")
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn update_with_trie <B, A>
    (x0: List<A>, f: Rc<dyn Fn(Option<B>) -> B>, x2: Trie<A, B>) -> Trie<A, B>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    match (x0, f, x2) {
        (List::Nil, f, Trie::Trie (v, p0)) =>
            {
                let ps = *p0;
                Trie::Trie (Option::Some ((*f)(v.clone())), Box::new(ps.clone()))
            },
        (List::Cons (k, p0), f, Trie::Trie (v, p1)) =>
            {
                let ks = *p0;
                let ps = *p1;
                Trie::Trie (v.clone(), Box::new(update_with_aux(empty_trie::<B,
                                    A>(), k.clone(), (({
     let f_cap = f.clone();
     let ks_cap = ks.clone();
     Rc::new(move |a: Trie<A, B>| -> Trie<A, B> {
         update_with_trie(ks_cap.clone(), f_cap.clone(), a.clone())
     })
 }) as Rc<dyn Fn(Trie<A, B>) -> Trie<A, B>>), ps.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn update_trie <B, A>
    (ks: List<A>, v: B) -> Rc<dyn Fn(Trie<A, B>) -> Trie<A, B>>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    (({
        let v_cap = v.clone();
        let ks_cap = ks.clone();
        Rc::new(move |a: Trie<A, B>| -> Trie<A, B> {
            update_with_trie(
                ks_cap.clone(),
                (({
                    let v_capa = v_cap.clone();
                    Rc::new(move |_: Option<B>| -> B {
                        v_capa.clone()
                    })
                }) as Rc<dyn Fn(Option<B>) -> B>),
                a.clone()
            )
        })
    }) as Rc<dyn Fn(Trie<A, B>) -> Trie<A, B>>)
}

pub fn map_trie <D, B, C, A>
    (f1: Rc<dyn Fn(A) -> B>, f2: Rc<dyn Fn(C) -> D>,
      x2: Trie<A, C>) -> Trie<B, D>
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static,
    D : Clone + 'static
{
    match (f1, f2, x2) {
        (f1, f2, Trie::Trie (x1, p0)) =>
            {
                let x2 = *p0;
                Trie::Trie (map_option(f2.clone(), x1.clone()), Box::new(mapa((({
                              let f2_cap = f2.clone();
                              let f1_cap = f1.clone();
                              Rc::new(move |a: (A, Trie<A,
                  C>)| -> (B, Trie<B, D>) {
                                  map_prod(f1_cap.clone(), (({
                                      let f2_capa = f2_cap.clone();
                                      let f1_capa = f1_cap.clone();
                                      Rc::new(move |aa: Trie<A,
                       C>| -> Trie<B, D> {
                                          map_trie(f1_capa.clone(), f2_capa.clone(), aa.clone())
                                      })
                                  }) as Rc<dyn Fn(Trie<A,
                 C>) -> Trie<B, D>>), a.clone())
                              })
                          }) as Rc<dyn Fn((A, Trie<A,
             C>)) -> (B, Trie<B, D>)>), x2.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rec_trie <C, A, B>
    (f: Rc<dyn Fn(Option<A>, List<(B, (Trie<B, A>, C))>) -> C>,
      x1: Trie<B, A>) -> C
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static
{
    match (f, x1) {
        (f, Trie::Trie (x1, p0)) =>
            {
                let x2 = *p0;
                (*f)(x1.clone(), mapa((({
                    let f_cap = f.clone();
                    Rc::new(move |a: (B, Trie<B, A>)| -> (B, (Trie<B, A>, C)) {
                        map_prod(
                            ((Rc::new(move |aa: B| -> B {
                                id(aa.clone())
                            })) as Rc<dyn Fn(B) -> B>),
                            (({
                                let f_capa = f_cap.clone();
                                Rc::new(move |trie: Trie<B,
                   A>| -> (Trie<B, A>, C) {
                                    (trie.clone(), rec_trie(f_capa.clone(), trie.clone()))
                                })
                            }) as Rc<dyn Fn(Trie<B, A>) -> (Trie<B, A>, C)>),
                            a.clone()
                        )
                    })
                }) as Rc<dyn Fn((B, Trie<B,
   A>)) -> (B, (Trie<B, A>, C))>), x2.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn rel_trie <D, B, C, A>
    (r1: Rc<dyn Fn(A, B) -> bool>, r2: Rc<dyn Fn(C, D) -> bool>, x2: Trie<A, C>,
      x3: Trie<B, D>) -> bool
where
    A : Clone + 'static,
    B : Clone + 'static,
    C : Clone + 'static,
    D : Clone + 'static
{
    match (r1, r2, x2, x3) {
        (r1, r2, Trie::Trie (x1, p0), Trie::Trie (y1, p1)) =>
            {
                let x2 = *p0;
                let y2 = *p1;
                rel_option(r2.clone(), x1.clone(), y1.clone()) &&
                  list_all2((({
                      let r2_cap = r2.clone();
                      let r1_cap = r1.clone();
                      Rc::new(move |a: (A, Trie<A,
          C>), b: (B, Trie<B, D>)| -> bool {
                          rel_prod(r1_cap.clone(), (({
                              let r2_capa = r2_cap.clone();
                              let r1_capa = r1_cap.clone();
                              Rc::new(move |aa: Trie<A,
               C>, ba: Trie<B, D>| -> bool {
                                  rel_trie(r1_capa.clone(), r2_capa.clone(), aa.clone(), ba.clone())
                              })
                          }) as Rc<dyn Fn(Trie<A, C>,
   Trie<B, D>) -> bool>), a.clone(), b.clone())
                      })
                  }) as Rc<dyn Fn((A, Trie<A, C>),
                                   (B, Trie<B,
      D>)) -> bool>), x2.clone(), y2.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn set1_trie <A, B> (x0: Trie<A, B>) -> Set<A>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    match x0 {
        Trie::Trie (_, p0) =>
            {
                let x2 = *p0;
                crate::Complete_Lattices::sup_set(image(
                    ((Rc::new(move |uu: (A, Trie<A, B>)| -> Set<A> {
                        crate::Set::sup_set((*fsts())(uu.clone()), crate::Complete_Lattices::sup_set(image(((Rc::new(move |a: Trie<A,
             B>| -> Set<A> {
                            set1_trie(a.clone())
                        })) as Rc<dyn Fn(Trie<A,
        B>) -> Set<A>>), (*snds())(uu.clone()))))
                    })) as Rc<dyn Fn((A, Trie<A, B>)) -> Set<A>>),
                    Set::Set (x2.clone())
                ))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn set2_trie <B, A> (x0: Trie<A, B>) -> Set<B>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    match x0 {
        Trie::Trie (x1, p0) =>
            {
                let x2 = *p0;
                crate::Set::sup_set(set_option(x1.clone()), crate::Complete_Lattices::sup_set(image(
                    ((Rc::new(move |uu: (A, Trie<A, B>)| -> Set<B> {
                        crate::Complete_Lattices::sup_set(image(((Rc::new(move |a: Trie<A,
          B>| -> Set<B> {
                            set2_trie(a.clone())
                        })) as Rc<dyn Fn(Trie<A,
        B>) -> Set<B>>), (*snds())(uu.clone())))
                    })) as Rc<dyn Fn((A, Trie<A, B>)) -> Set<B>>),
                    Set::Set (x2.clone())
                )))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_trie <B, A>
    (xa: Rc<dyn Fn(A) -> BigInt>, x: Rc<dyn Fn(B) -> BigInt>,
      xb2: Trie<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (xa, x, xb2) {
        (xa, x, Trie::Trie (x1, p0)) =>
            {
                let x2 = *p0;
                size_option(x.clone(), x1.clone()) +
                  size_list((({
                      let x_cap = x.clone();
                      let xa_cap = xa.clone();
                      Rc::new(move |a: (A, Trie<A, B>)| -> BigInt {
                          size_prod(xa_cap.clone(), (({
                              let x_capa = x_cap.clone();
                              let xa_capa = xa_cap.clone();
                              Rc::new(move |aa: Trie<A, B>| -> BigInt {
                                  size_trie(xa_capa.clone(), x_capa.clone(), aa.clone())
                              })
                          }) as Rc<dyn Fn(Trie<A, B>) -> BigInt>), a.clone())
                      })
                  }) as Rc<dyn Fn((A, Trie<A, B>)) -> BigInt>), x2.clone()) +
                  suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn size_triea <B, A> (x0: Trie<A, B>) -> BigInt
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match x0 {
        Trie::Trie (x1, p0) =>
            {
                let x2 = *p0;
                size_optiona(x1.clone()) +
                  size_list(((Rc::new(move |a: (A, Trie<A, B>)| -> BigInt {
                      size_prod(
                          ((Rc::new(move |_: A| -> BigInt {
                              BigInt::ZERO
                          })) as Rc<dyn Fn(A) -> BigInt>),
                          ((Rc::new(move |aa: Trie<A, B>| -> BigInt {
                              size_triea(aa.clone())
                          })) as Rc<dyn Fn(Trie<A, B>) -> BigInt>),
                          a.clone()
                      )
                  })) as Rc<dyn Fn((A, Trie<A, B>)) -> BigInt>), x2.clone()) +
                  suc(BigInt::ZERO)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static, 
       C : Clone + Typerep + 'static>
    Typerep for TriePreTrie<A, B, C> {
    fn typerep (x0: Itself<TriePreTrie<A, B, C>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, false, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Cons (<C as Typerep>::typerep(Itself::Type (PhantomData::<C>)), Box::new(List::Nil))))))))
    }
}

impl <A : Clone + Typerep + 'static,  B : Clone + Typerep + 'static> Typerep for
    TrieIITNTrie<A, B> {
    fn typerep (x0: Itself<TrieIITNTrie<A, B>>) -> Typerepa {
        Typerepa::Typerep (Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (false, true, true, true, false, true, false, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (true, false, false, true, false, false, true, Box::new(Literal::Literal (false, false, true, false, true, false, true, Box::new(Literal::Literal (false, true, true, true, false, false, true, Box::new(Literal::Literal (true, true, true, true, true, false, true, Box::new(Literal::Literal (false, false, true, false, true, true, true, Box::new(Literal::Literal (false, true, false, false, true, true, true, Box::new(Literal::Literal (true, false, false, true, false, true, true, Box::new(Literal::Literal (true, false, true, false, false, true, true, Box::new(Literal::ZeroLiteral)))))))))))))))))))))))))))))))))))))))))))))))), Box::new(List::Cons (<A as Typerep>::typerep(Itself::Type (PhantomData::<A>)), Box::new(List::Cons (<B as Typerep>::typerep(Itself::Type (PhantomData::<B>)), Box::new(List::Nil))))))
    }
}
