use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::one_nat;
use crate::Arith::suc;
use crate::Euclidean_Rings::divide_nat;
use crate::Finite_Set::card;
use crate::List::List;
use crate::List::drop;
use crate::List::nth;
use crate::List::size_list;
use crate::List::take;
use crate::List::upt;
use crate::Orderings::Linorder;
use crate::Orderings::Ord;
use crate::Orderings::Preorder;
use crate::Product_Type::product;
use crate::Product_Type::sigma;
use crate::Set::Set;
use crate::Set::filter;

use std::rc::Rc;

pub fn merge_lists <A> (x0: List<A>, ys: List<A>) -> List<A>
where
    A : Clone + Linorder + 'static
{
    match (x0, ys) {
        (List::Nil, ys) =>
            ys.clone(),
        (List::Cons (v, p0), List::Nil) =>
            {
                let va = *p0;
                List::Cons (v.clone(), Box::new(va.clone()))
            },
        (List::Cons (x, p0), List::Cons (y, p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                if <A as Ord>::less_eq(x.clone(), y.clone()) {
                    List::Cons (x.clone(), Box::new(merge_lists(xs.clone(), List::Cons (y.clone(), Box::new(ys.clone())))))
                } else {
                    List::Cons (y.clone(), Box::new(merge_lists(List::Cons (x.clone(), Box::new(xs.clone())), ys.clone())))
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn merge_sort <A> (xs: List<A>) -> List<A>
where
    A : Clone + Linorder + 'static
{
    if size_list(xs.clone()) <= one_nat() {
        xs.clone()
    } else {
        merge_lists(merge_sort(take(divide_nat(size_list(xs.clone()), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), xs.clone())), merge_sort(drop(divide_nat(size_list(xs.clone()), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), xs.clone())))
    }
}

pub fn split_list <A> (xs: List<A>) -> (List<A>, List<A>)
where
    A : Clone + 'static
{
    let n = divide_nat(size_list(xs.clone()), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } }));
    (take(n.clone(), xs.clone()), drop(n.clone(), xs.clone()))
}

pub fn inversions <A> (xs: List<A>) -> Set<(BigInt, BigInt)>
where
    A : Clone + Preorder + 'static
{
    sigma(
        Set::Set (upt(BigInt::ZERO, size_list(xs.clone()))),
        (({
            let xs_cap = xs.clone();
            Rc::new(move |i: BigInt| -> Set<BigInt> {
                filter(
                    (({
                        let i_cap = i.clone();
                        let xs_capa = xs_cap.clone();
                        Rc::new(move |j: BigInt| -> bool {
                            <A as Ord>::less(nth(xs_capa.clone(), j.clone()), nth(xs_capa.clone(), i_cap.clone()))
                        })
                    }) as Rc<dyn Fn(BigInt) -> bool>),
                    Set::Set (upt(suc(i.clone()), size_list(xs_cap.clone())))
                )
            })
        }) as Rc<dyn Fn(BigInt) -> Set<BigInt>>)
    )
}

pub fn inversion_number <A> (xs: List<A>) -> BigInt
where
    A : Clone + Preorder + 'static
{
    card(inversions(xs.clone()))
}

pub fn inversions_between <A>
    (xs: List<A>, ys: List<A>) -> Set<(BigInt, BigInt)>
where
    A : Clone + Preorder + 'static
{
    filter(
        (({
            let xs_cap = xs.clone();
            let ys_cap = ys.clone();
            Rc::new(move |(i, j): (BigInt, BigInt)| -> bool {
                <A as Ord>::less(nth(ys_cap.clone(), j.clone()), nth(xs_cap.clone(), i.clone()))
            })
        }) as Rc<dyn Fn((BigInt, BigInt)) -> bool>),
        product(Set::Set (upt(BigInt::ZERO, size_list(xs.clone()))), Set::Set (upt(BigInt::ZERO, size_list(ys.clone()))))
    )
}

pub fn inversion_number_between <A> (xs: List<A>, ys: List<A>) -> BigInt
where
    A : Clone + Preorder + 'static
{
    card(inversions_between(xs.clone(), ys.clone()))
}

pub fn inversion_number_between_sorted <A> (x0: List<A>, x1: List<A>) -> BigInt
where
    A : Clone + Preorder + 'static
{
    match (x0, x1) {
        (List::Nil, _) =>
            BigInt::ZERO,
        (List::Cons (_, _), List::Nil) =>
            BigInt::ZERO,
        (List::Cons (x, p0), List::Cons (y, p1)) =>
            {
                let xs = *p0;
                let ys = *p1;
                if ! <A as Ord>::less(y.clone(), x.clone()) {
                    inversion_number_between_sorted(xs.clone(), List::Cons (y.clone(), Box::new(ys.clone())))
                } else {
                    inversion_number_between_sorted(List::Cons (x.clone(), Box::new(xs.clone())), ys.clone()) +
                      size_list(List::Cons (x.clone(), Box::new(xs.clone())))
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn sort_and_count_inversions <A> (xs: List<A>) -> (List<A>, BigInt)
where
    A : Clone + Linorder + 'static
{
    if size_list(xs.clone()) <= one_nat() {
        (xs.clone(), BigInt::ZERO)
    } else {
        match split_list(xs.clone()) {
            (xs1, xs2) =>
                match sort_and_count_inversions(xs1.clone()) {
                    (xs1a, m) =>
                        match sort_and_count_inversions(xs2.clone()) {
                            (xs2a, n) =>
                                (merge_lists(xs1a.clone(), xs2a.clone()), m.clone() +
                                    n.clone() +
                                    inversion_number_between_sorted(xs1a.clone(), xs2a.clone())),
                            _ =>
                                panic!("non-exhaustive match")
                        },
                    _ =>
                        panic!("non-exhaustive match")
                },
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
