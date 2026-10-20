use crate::Enum::Enum;
use crate::HOL::Equal;
use crate::HOL::eq;
use crate::List::List;
use crate::List::mapa;
use crate::List::maps;
use crate::List::remove1;
use crate::List::sorted_list_of_set;
use crate::Orderings::Linorder;
use crate::Set::Set;
use crate::Set::ball;
use crate::Set::bot_set;
use crate::Set::collect;
use crate::Set::image;
use crate::Set::inf_set;
use crate::Set::insert;
use crate::Set::is_empty;
use crate::Set::remove;

use std::rc::Rc;

pub fn is_non_overlapping <A> (p: Set<Set<A>>) -> bool
where
    A : Clone + Equal + 'static
{
    ball(
        p.clone(),
        (({
            let p_cap = p.clone();
            Rc::new(move |x: Set<A>| -> bool {
                ball(
                    p_cap.clone(),
                    (({
                        let x_cap = x.clone();
                        Rc::new(move |y: Set<A>| -> bool {
                            <bool as Equal>::equal(! is_empty(inf_set(x_cap.clone(), y.clone())), eq(x_cap.clone(), y.clone()))
                        })
                    }) as Rc<dyn Fn(Set<A>) -> bool>)
                )
            })
        }) as Rc<dyn Fn(Set<A>) -> bool>)
    )
}

pub fn is_partition_of <A> (p: Set<Set<A>>, a: Set<A>) -> bool
where
    A : Clone + Equal + 'static
{
    eq(crate::Complete_Lattices::sup_set(p.clone()), a.clone()) &&
      is_non_overlapping(p.clone())
}

pub fn all_partitions <A> (a: Set<A>) -> Set<Set<Set<A>>>
where
    A : Clone + Enum + Equal + 'static
{
    collect(
        (({
            let a_cap = a.clone();
            Rc::new(move |p: Set<Set<A>>| -> bool {
                is_partition_of(p.clone(), a_cap.clone())
            })
        }) as Rc<dyn Fn(Set<Set<A>>) -> bool>)
    )
}

pub fn partition_without <A> (elem: A, p: Set<Set<A>>) -> Set<Set<A>>
where
    A : Clone + Equal + 'static
{
    remove(bot_set::<A>(), image((({
        let elem_cap = elem.clone();
        Rc::new(move |a: Set<A>| -> Set<A> {
            remove(elem_cap.clone(), a.clone())
        })
    }) as Rc<dyn Fn(Set<A>) -> Set<A>>), p.clone()))
}

pub fn insert_into_member_list <A>
    (new_el: A, sets: List<Set<A>>, s: Set<A>) -> List<Set<A>>
where
    A : Clone + Equal + 'static
{
    List::Cons (crate::Set::sup_set(s.clone(), insert(new_el.clone(), bot_set::<A>())), Box::new(remove1(s.clone(), sets.clone())))
}

pub fn coarser_partitions_with_list <A>
    (new_el: A, p: List<Set<A>>) -> List<List<Set<A>>>
where
    A : Clone + Equal + 'static
{
    List::Cons (List::Cons (insert(new_el.clone(), bot_set::<A>()), Box::new(p.clone())), Box::new(mapa((({
                let p_cap = p.clone();
                let new_el_cap = new_el.clone();
                Rc::new(move |a: Set<A>| -> List<Set<A>> {
                    insert_into_member_list(new_el_cap.clone(), p_cap.clone(), a.clone())
                })
            }) as Rc<dyn Fn(Set<A>) -> List<Set<A>>>), p.clone())))
}

pub fn all_coarser_partitions_with_list <A>
    (elem: A, ps: List<List<Set<A>>>) -> List<List<Set<A>>>
where
    A : Clone + Equal + 'static
{
    maps((({
        let elem_cap = elem.clone();
        Rc::new(move |a: List<Set<A>>| -> List<List<Set<A>>> {
            coarser_partitions_with_list(elem_cap.clone(), a.clone())
        })
    }) as Rc<dyn Fn(List<Set<A>>) -> List<List<Set<A>>>>), ps.clone())
}

pub fn all_partitions_list <A> (x0: List<A>) -> List<List<Set<A>>>
where
    A : Clone + Equal + 'static
{
    match x0 {
        List::Nil =>
            List::Cons (List::Nil, Box::new(List::Nil)),
        List::Cons (e, p0) =>
            {
                let x = *p0;
                all_coarser_partitions_with_list(e.clone(), all_partitions_list(x.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn all_partitions_alg <A> (x: Set<A>) -> List<List<Set<A>>>
where
    A : Clone + Equal + Linorder + 'static
{
    all_partitions_list(sorted_list_of_set(x.clone()))
}

pub fn insert_into_member <A>
    (new_el: A, sets: Set<Set<A>>, s: Set<A>) -> Set<Set<A>>
where
    A : Clone + Equal + 'static
{
    insert(crate::Set::sup_set(s.clone(), insert(new_el.clone(), bot_set::<A>())), remove(s.clone(), sets.clone()))
}

pub fn coarser_partitions_with <A>
    (new_el: A, p: Set<Set<A>>) -> Set<Set<Set<A>>>
where
    A : Clone + Equal + 'static
{
    insert(insert(insert(new_el.clone(), bot_set::<A>()), p.clone()), image((({
        let p_cap = p.clone();
        let new_el_cap = new_el.clone();
        Rc::new(move |a: Set<A>| -> Set<Set<A>> {
            insert_into_member(new_el_cap.clone(), p_cap.clone(), a.clone())
        })
    }) as Rc<dyn Fn(Set<A>) -> Set<Set<A>>>), p.clone()))
}

pub fn all_coarser_partitions_with <A>
    (elem: A, ps: Set<Set<Set<A>>>) -> Set<Set<Set<A>>>
where
    A : Clone + Equal + 'static
{
    crate::Complete_Lattices::sup_set(image((({
        let elem_cap = elem.clone();
        Rc::new(move |a: Set<Set<A>>| -> Set<Set<Set<A>>> {
            coarser_partitions_with(elem_cap.clone(), a.clone())
        })
    }) as Rc<dyn Fn(Set<Set<A>>) -> Set<Set<Set<A>>>>), ps.clone()))
}

pub fn all_partitions_set <A> (x0: List<A>) -> Set<Set<Set<A>>>
where
    A : Clone + Equal + 'static
{
    match x0 {
        List::Nil =>
            insert(bot_set::<Set<A>>(), bot_set::<Set<Set<A>>>()),
        List::Cons (e, p0) =>
            {
                let x = *p0;
                all_coarser_partitions_with(e.clone(), all_partitions_set(x.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}
