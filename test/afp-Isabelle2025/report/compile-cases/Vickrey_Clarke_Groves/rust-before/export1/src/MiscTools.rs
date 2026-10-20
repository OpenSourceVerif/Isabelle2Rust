use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::One;
use crate::Enum::Enum;
use crate::Euclidean_Rings::divide_nat;
use crate::Euclidean_Rings::modulo_nat;
use crate::HOL::Equal;
use crate::HOL::ex;
use crate::HOL::the;
use crate::List::List;
use crate::List::rotate;
use crate::List::size_list;
use crate::Relation::domain;
use crate::RelationOperators::eval_rel;
use crate::RelationOperators::paste;
use crate::RelationOperators::restrict;
use crate::RelationOperators::runiq;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::collect;
use crate::Set::insert;
use crate::Set::member;

use std::rc::Rc;

pub fn graph <B, A> (f: Rc<dyn Fn(A) -> B>) -> Set<(A, B)>
where
    A : Clone + Enum + Equal + 'static,
    B : Clone + Enum + Equal + 'static
{
    collect(
        (({
            let f_cap = f.clone();
            Rc::new(move |uu: (A, B)| -> bool {
                ex(
                    (({
                        let f_capa = f_cap.clone();
                        let uu_cap = uu.clone();
                        Rc::new(move |x: A| -> bool {
                            <(A, B) as Equal>::equal(uu_cap.clone(), (x.clone(), (*f_capa)(x.clone()))) &&
                              true
                        })
                    }) as Rc<dyn Fn(A) -> bool>)
                )
            })
        }) as Rc<dyn Fn((A, B)) -> bool>)
    )
}

pub fn grapha <B, A> (x: Set<A>, f: Rc<dyn Fn(A) -> B>) -> Set<(A, B)>
where
    A : Clone + 'static,
    B : Clone + 'static
{
    crate::Set::image(
        (({
            let f_cap = f.clone();
            Rc::new(move |xa: A| -> (A, B) {
                (xa.clone(), (*f_cap)(xa.clone()))
            })
        }) as Rc<dyn Fn(A) -> (A, B)>),
        x.clone()
    )
}

pub fn perm2 <A> (x0: List<A>) -> Rc<dyn Fn(BigInt) -> List<A>>
where
    A : Clone + 'static
{
    match x0 {
        List::Nil =>
            ((Rc::new(move |_: BigInt| -> List<A> {
                List::Nil
            })) as Rc<dyn Fn(BigInt) -> List<A>>),
        List::Cons (x, p0) =>
            {
                let l = *p0;
                (({
                    let l_cap = l.clone();
                    let x_cap = x.clone();
                    Rc::new(move |n: BigInt| -> List<A> {
                        (*rotate((match (size_list(List::Cons (x_cap.clone(), Box::new((*rotate(modulo_nat(n.clone(), <BigInt as One>::one() +
size_list(l_cap.clone()))))((*perm2(l_cap.clone()))(divide_nat(n.clone(), <BigInt as One>::one() +
                                    size_list(l_cap.clone()))))))).clone(), modulo_nat(modulo_nat(n.clone(), <BigInt as One>::one() +
                               size_list(l_cap.clone())), size_list(List::Cons (x_cap.clone(), Box::new((*rotate(modulo_nat(n.clone(), <BigInt as One>::one() +
                 size_list(l_cap.clone()))))((*perm2(l_cap.clone()))(divide_nat(n.clone(), <BigInt as One>::one() +
             size_list(l_cap.clone())))))))).clone()) { (m, n) => if m <= n { BigInt::ZERO } else { m - n } })))(List::Cons (x_cap.clone(), Box::new((*rotate(modulo_nat(n.clone(), <BigInt as One>::one() +
                      size_list(l_cap.clone()))))((*perm2(l_cap.clone()))(divide_nat(n.clone(), <BigInt as One>::one() +
                  size_list(l_cap.clone())))))))
                    })
                }) as Rc<dyn Fn(BigInt) -> List<A>>)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn runiqs <B, A> () -> Set<Set<(A, B)>>
where
    A : Clone + Enum + Equal + 'static,
    B : Clone + Enum + Equal + 'static
{
    collect(((Rc::new(move |a: Set<(A, B)>| -> bool {
        runiq(a.clone())
    })) as Rc<dyn Fn(Set<(A, B)>) -> bool>))
}

pub fn update <B, A> (p: Set<(A, B)>, q: Set<(A, B)>) -> Set<(A, B)>
where
    A : Clone + Equal + 'static,
    B : Clone + Equal + 'static
{
    paste(p.clone(), restrict(q.clone(), domain(p.clone())))
}

pub fn runiqer <B, A> (r: Set<(A, B)>) -> Set<(A, B)>
where
    A : Clone + Equal + 'static,
    B : Clone + Enum + Equal + 'static
{
    crate::Set::image(
        (({
            let r_cap = r.clone();
            Rc::new(move |x: A| -> (A, B) {
                (x.clone(), the(
                    (({
                        let x_cap = x.clone();
                        let r_capa = r_cap.clone();
                        Rc::new(move |y: B| -> bool {
                            member(y.clone(), crate::Relation::image(r_capa.clone(), insert(x_cap.clone(), bot_set::<A>())))
                        })
                    }) as Rc<dyn Fn(B) -> bool>)
                ))
            })
        }) as Rc<dyn Fn(A) -> (A, B)>),
        domain(r.clone())
    )
}

pub fn finestpart <A> (x: Set<A>) -> Set<Set<A>>
where
    A : Clone + Equal + 'static
{
    crate::Set::image(
        ((Rc::new(move |xa: A| -> Set<A> {
            insert(xa.clone(), bot_set::<A>())
        })) as Rc<dyn Fn(A) -> Set<A>>),
        x.clone()
    )
}

pub fn to_function <B, A> (r: Set<(A, B)>) -> Rc<dyn Fn(A) -> B>
where
    A : Clone + Equal + 'static,
    B : Clone + 'static
{
    (({
        let r_cap = r.clone();
        Rc::new(move |a: A| -> B {
            eval_rel(r_cap.clone(), a.clone())
        })
    }) as Rc<dyn Fn(A) -> B>)
}
