use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::One;
use crate::Arith::of_nat;
use crate::Arith::suc;
use crate::Fields::Inverse;
use crate::Groups_List::sum_list;
use crate::List::List;
use crate::List::mapa;
use crate::List::upt;
use crate::Real_Vector_Spaces::RealNormedField;

use std::rc::Rc;

pub fn harm <A> (n: BigInt) -> A
where
    A : Clone + RealNormedField + 'static
{
    sum_list(mapa(
        ((Rc::new(move |k: BigInt| -> A {
            <A as Inverse>::inverse(of_nat::<A>(k.clone()))
        })) as Rc<dyn Fn(BigInt) -> A>),
        upt(<BigInt as One>::one(), suc(n.clone()))
    ))
}
