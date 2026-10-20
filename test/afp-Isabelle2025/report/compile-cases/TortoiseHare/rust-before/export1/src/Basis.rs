use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::funpow;
use crate::Enum::Enum;
use crate::Finite_Set::Finite;
use crate::HOL::all;
use crate::HOL::implies;

use std::rc::Rc;

pub fn valid <A>
    (p: Rc<dyn Fn(A) -> bool>, c: Rc<dyn Fn(A) -> A>,
      q: Rc<dyn Fn(A) -> bool>) -> bool
where
    A : Clone + Enum + 'static
{
    all(
        (({
            let c_cap = c.clone();
            let q_cap = q.clone();
            let p_cap = p.clone();
            Rc::new(move |s: A| -> bool {
                implies((*p_cap)(s.clone()), (*q_cap)((*c_cap)(s.clone())))
            })
        }) as Rc<dyn Fn(A) -> bool>)
    )
}

pub fn seq <A> (f: Rc<dyn Fn(A) -> A>, x: A, i: BigInt) -> A
where
    A : Clone + Finite + 'static
{
    (*funpow(i.clone(), f.clone()))(x.clone())
}
