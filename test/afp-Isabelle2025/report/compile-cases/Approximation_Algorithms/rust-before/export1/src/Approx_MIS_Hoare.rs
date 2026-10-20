use crate::Complete_Lattices::sup_set;
use crate::Enum::Enum;
use crate::HOL::Equal;
use crate::HOL::all;
use crate::HOL::implies;
use crate::Orderings::Ord;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::insert;
use crate::Set::member;

use std::rc::Rc;

pub fn independent_vertices <A> (e: Set<Set<A>>, s: Set<A>) -> bool
where
    A : Clone + Enum + Equal + 'static
{
    <Set<A> as Ord>::less_eq(s.clone(), sup_set(e.clone())) &&
      all(
          (({
              let e_cap = e.clone();
              let s_cap = s.clone();
              Rc::new(move |v1: A| -> bool {
                  all(
                      (({
                          let e_capa = e_cap.clone();
                          let s_capa = s_cap.clone();
                          let v1_cap = v1.clone();
                          Rc::new(move |v2: A| -> bool {
                              implies(member(v1_cap.clone(), s_capa.clone()) &&
member(v2.clone(), s_capa.clone()), ! member(insert(v1_cap.clone(), insert(v2.clone(), bot_set::<A>())), e_capa.clone()))
                          })
                      }) as Rc<dyn Fn(A) -> bool>)
                  )
              })
          }) as Rc<dyn Fn(A) -> bool>)
      )
}
