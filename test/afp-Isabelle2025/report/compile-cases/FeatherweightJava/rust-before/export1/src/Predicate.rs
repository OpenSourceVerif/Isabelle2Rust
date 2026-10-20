use crate::HOL::Equal;
use crate::HOL::eq;
use crate::Product_Type::Unit;

use std::rc::Rc;

#[derive(Clone)]
pub enum Seq<A> {
    Empty,
    Insert (A, Box<Pred<A>>),
    Join (Box<Pred<A>>, Box<Seq<A>>)
}
#[derive(Clone)]
pub enum Pred<A> {
    Seq (Box<Rc<dyn Fn(Unit) -> Seq<A>>>)
}

pub fn bind <B, A> (x0: Pred<A>, f: Rc<dyn Fn(A) -> Pred<B>>) -> Pred<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (x0, f) {
        (Pred::Seq (p0), f) =>
            {
                let g = *p0;
                Pred::Seq (
                    Box::new((({
                          let g_cap = g.clone();
                          let f_cap = f.clone();
                          Rc::new(move |_: Unit| -> Seq<B> {
                              apply(f_cap.clone(), (*g_cap)(Unit::Unity))
                          })
                      }) as Rc<dyn Fn(Unit) -> Seq<B>>))
                )
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn apply <B, A> (f: Rc<dyn Fn(A) -> Pred<B>>, x1: Seq<A>) -> Seq<B>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    match (f, x1) {
        (_, Seq::Empty) =>
            Seq::Empty,
        (f, Seq::Insert (x, p0)) =>
            {
                let p = *p0;
                Seq::Join (Box::new((*f)(x.clone())), Box::new(Seq::Join (Box::new(bind(p.clone(), f.clone())), Box::new(Seq::Empty))))
            },
        (f, Seq::Join (p0, p1)) =>
            {
                let p = *p0;
                let xq = *p1;
                Seq::Join (Box::new(bind(p.clone(), f.clone())), Box::new(apply(f.clone(), xq.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn eval <A> (x0: Pred<A>) -> Rc<dyn Fn(A) -> bool>
where
    A : Clone + Equal + 'static
{
    match x0 {
        Pred::Seq (p0) =>
            {
                let f = *p0;
                (({
                    let f_cap = f.clone();
                    Rc::new(move |a: A| -> bool {
                        member((*f_cap)(Unit::Unity), a.clone())
                    })
                }) as Rc<dyn Fn(A) -> bool>)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn member <A> (xa0: Seq<A>, x: A) -> bool
where
    A : Clone + Equal + 'static
{
    match (xa0, x) {
        (Seq::Empty, _) =>
            false,
        (Seq::Insert (y, p0), x) =>
            {
                let p = *p0;
                eq(x.clone(), y.clone()) || (*eval(p.clone()))(x.clone())
            },
        (Seq::Join (p0, p1), x) =>
            {
                let p = *p0;
                let xq = *p1;
                (*eval(p.clone()))(x.clone()) || member(xq.clone(), x.clone())
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn holds (p: Pred<Unit>) -> bool {
    (*eval(p.clone()))(Unit::Unity)
}

pub fn bot_pred <A> () -> Pred<A>
where
    A : Clone + 'static
{
    Pred::Seq (
        Box::new(((Rc::new(move |_: Unit| -> Seq<A> {
              Seq::Empty
          })) as Rc<dyn Fn(Unit) -> Seq<A>>))
    )
}

pub fn single <A> (x: A) -> Pred<A>
where
    A : Clone + 'static
{
    Pred::Seq (
        Box::new((({
              let x_cap = x.clone();
              Rc::new(move |_: Unit| -> Seq<A> {
                  Seq::Insert (x_cap.clone(), Box::new(bot_pred::<A>()))
              })
          }) as Rc<dyn Fn(Unit) -> Seq<A>>))
    )
}

pub fn adjunct <A> (p: Pred<A>, x1: Seq<A>) -> Seq<A>
where
    A : Clone + 'static
{
    match (p, x1) {
        (p, Seq::Empty) =>
            Seq::Join (Box::new(p.clone()), Box::new(Seq::Empty)),
        (p, Seq::Insert (x, p0)) =>
            {
                let q = *p0;
                Seq::Insert (x.clone(), Box::new(sup_pred(q.clone(), p.clone())))
            },
        (p, Seq::Join (p0, p1)) =>
            {
                let q = *p0;
                let xq = *p1;
                Seq::Join (Box::new(q.clone()), Box::new(adjunct(p.clone(), xq.clone())))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn sup_pred <A> (x0: Pred<A>, x1: Pred<A>) -> Pred<A>
where
    A : Clone + 'static
{
    match (x0, x1) {
        (Pred::Seq (p0), Pred::Seq (p1)) =>
            {
                let f = *p0;
                let g = *p1;
                Pred::Seq (
                    Box::new((({
                          let g_cap = g.clone();
                          let f_cap = f.clone();
                          Rc::new(move |_: Unit| -> Seq<A> {
                              match (*f_cap)(Unit::Unity) {
                                  Seq::Empty =>
                                      (*g_cap)(Unit::Unity),
                                  Seq::Insert (x, p0) =>
                                      {
                                          let p = *p0;
  Seq::Insert (x.clone(), Box::new(sup_pred(p.clone(), Pred::Seq (Box::new(g_cap.clone())))))
                                      },
                                  Seq::Join (p0, p1) =>
                                      {
                                          let p = *p0;
  let xq = *p1;
  adjunct(Pred::Seq (Box::new(g_cap.clone())), Seq::Join (Box::new(p.clone()), Box::new(xq.clone())))
                                      },
                                  _ =>
                                      panic!("non-exhaustive match")
                              }
                          })
                      }) as Rc<dyn Fn(Unit) -> Seq<A>>))
                )
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn if_pred (b: bool) -> Pred<Unit> {
    if b.clone() {
        single(Unit::Unity)
    } else {
        bot_pred::<Unit>()
    }
}

pub fn not_pred (p: Pred<Unit>) -> Pred<Unit> {
    if (*eval(p.clone()))(Unit::Unity) {
        bot_pred::<Unit>()
    } else {
        single(Unit::Unity)
    }
}
