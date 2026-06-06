use num_bigint::*;
use num_traits::sign::*;

use crate::Product_Type::*;

#[derive(Clone)]
pub enum CopyWrap<A> { 
  CopyWrap (A)
}

pub fn duplicate_wrap <A>
  (x: CopyWrap<A>) -> Prod<CopyWrap<A>, CopyWrap<A>>
    where
      A : Clone
     {
    match x{x => Prod::Pair (x.clone(), x.clone())}
  }

pub fn duplicate_value <A>
  (x: A) -> Prod<A, A>
    where
      A : Clone
     {
    match x{x => Prod::Pair (x.clone(), x.clone())}
  }
