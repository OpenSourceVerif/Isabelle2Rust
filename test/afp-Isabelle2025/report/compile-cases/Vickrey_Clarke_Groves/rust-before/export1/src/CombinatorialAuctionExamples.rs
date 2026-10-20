use num_bigint::*;
use num_traits::sign::Signed as _;

use crate::Arith::Num;
use crate::Arith::Numeral;
use crate::Arith::One;
use crate::Arith::Zero;
use crate::Arith::numeral;
use crate::CombinatorialAuction::vcga_alg;
use crate::List::List;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::insert;
use crate::UniformTieBreaking::to_function_with_fallback_alg;

use std::rc::Rc;

pub fn n1 () -> Set<BigInt> {
    insert(BigInt::from_bytes_be(Sign::Plus, &[1]), insert(BigInt::from_bytes_be(Sign::Plus, &[2]), insert(BigInt::from_bytes_be(Sign::Plus, &[3]), bot_set::<BigInt>())))
}

pub fn n2 () -> Set<BigInt> {
    insert(BigInt::from_bytes_be(Sign::Plus, &[1]), insert(BigInt::from_bytes_be(Sign::Plus, &[2]), insert(BigInt::from_bytes_be(Sign::Plus, &[3]), bot_set::<BigInt>())))
}

pub fn n3 () -> Set<BigInt> {
    insert(BigInt::from_bytes_be(Sign::Plus, &[1]), insert(BigInt::from_bytes_be(Sign::Plus, &[2]), insert(BigInt::from_bytes_be(Sign::Plus, &[3]), bot_set::<BigInt>())))
}

pub fn b1 () -> Set<((BigInt, Set<BigInt>), BigInt)> {
    insert(((BigInt::from_bytes_be(Sign::Plus, &[1]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), bot_set::<BigInt>()))), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[2]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[2]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[3]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[3]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), bot_set::<((BigInt, Set<BigInt>), BigInt)>())))))
}

pub fn b2 () -> Set<((BigInt, Set<BigInt>), BigInt)> {
    insert(((BigInt::from_bytes_be(Sign::Plus, &[1]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), bot_set::<BigInt>()))), (match BigInt::from_bytes_be(Sign::Plus, &[5]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[2]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[3]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[2]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[3]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[3]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[3]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[4]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), bot_set::<((BigInt, Set<BigInt>), BigInt)>())))))
}

pub fn b3 () -> Set<((BigInt, Set<BigInt>), BigInt)> {
    insert(((BigInt::from_bytes_be(Sign::Plus, &[1]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), insert(BigInt::from_bytes_be(Sign::Plus, &[13]), bot_set::<BigInt>())))), (match BigInt::from_bytes_be(Sign::Plus, &[20]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[1]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), bot_set::<BigInt>()))), (match BigInt::from_bytes_be(Sign::Plus, &[18]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[2]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[10]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[2]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[15]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[2]), insert(BigInt::from_bytes_be(Sign::Plus, &[13]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[15]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[2]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), insert(BigInt::from_bytes_be(Sign::Plus, &[13]), bot_set::<BigInt>()))), (match BigInt::from_bytes_be(Sign::Plus, &[18]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[3]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), bot_set::<BigInt>())), (match BigInt::from_bytes_be(Sign::Plus, &[2]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[3]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), bot_set::<BigInt>()))), (match BigInt::from_bytes_be(Sign::Plus, &[12]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[3]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), insert(BigInt::from_bytes_be(Sign::Plus, &[13]), bot_set::<BigInt>()))), (match BigInt::from_bytes_be(Sign::Plus, &[17]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[3]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), insert(BigInt::from_bytes_be(Sign::Plus, &[13]), bot_set::<BigInt>()))), (match BigInt::from_bytes_be(Sign::Plus, &[18]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), insert(((BigInt::from_bytes_be(Sign::Plus, &[3]), insert(BigInt::from_bytes_be(Sign::Plus, &[11]), insert(BigInt::from_bytes_be(Sign::Plus, &[12]), insert(BigInt::from_bytes_be(Sign::Plus, &[13]), bot_set::<BigInt>())))), (match BigInt::from_bytes_be(Sign::Plus, &[19]).clone() { k => if k <= BigInt::ZERO { BigInt::ZERO } else { k } })), bot_set::<((BigInt, Set<BigInt>), BigInt)>())))))))))))
}

pub fn r1 <A> () -> A
where
    A : Clone + Zero + 'static
{
    <A as Zero>::zero()
}

pub fn r2 <A> () -> A
where
    A : Clone + One + 'static
{
    <A as One>::one()
}

pub fn r3 <A> () -> A
where
    A : Clone + Zero + 'static
{
    <A as Zero>::zero()
}

pub fn omega_1 <A> () -> List<A>
where
    A : Clone + Numeral + 'static
{
    List::Cons (numeral::<A>(Num::Bit1 (Box::new(Num::Bit1 (Box::new(Num::Bit0 (Box::new(Num::One))))))), Box::new(List::Cons (numeral::<A>(Num::Bit0 (Box::new(Num::Bit0 (Box::new(Num::Bit1 (Box::new(Num::One))))))), Box::new(List::Nil))))
}

pub fn vcga1 () -> Set<(BigInt, Set<BigInt>)> {
    vcga_alg(n1(), omega_1::<BigInt>(), ((Rc::new(move |a: (BigInt, Set<BigInt>)| -> BigInt {
        (*to_function_with_fallback_alg(b1(), BigInt::ZERO))(a.clone())
    })) as Rc<dyn Fn((BigInt, Set<BigInt>)) -> BigInt>), r1::<BigInt>())
}

pub fn omega_2 <A> () -> List<A>
where
    A : Clone + Numeral + 'static
{
    List::Cons (numeral::<A>(Num::Bit1 (Box::new(Num::Bit1 (Box::new(Num::Bit0 (Box::new(Num::One))))))), Box::new(List::Cons (numeral::<A>(Num::Bit0 (Box::new(Num::Bit0 (Box::new(Num::Bit1 (Box::new(Num::One))))))), Box::new(List::Nil))))
}

pub fn vcga2 () -> Set<(BigInt, Set<BigInt>)> {
    vcga_alg(n2(), omega_2::<BigInt>(), ((Rc::new(move |a: (BigInt, Set<BigInt>)| -> BigInt {
        (*to_function_with_fallback_alg(b2(), BigInt::ZERO))(a.clone())
    })) as Rc<dyn Fn((BigInt, Set<BigInt>)) -> BigInt>), r2::<BigInt>())
}

pub fn omega_3 <A> () -> List<A>
where
    A : Clone + Numeral + 'static
{
    List::Cons (numeral::<A>(Num::Bit1 (Box::new(Num::Bit1 (Box::new(Num::Bit0 (Box::new(Num::One))))))), Box::new(List::Cons (numeral::<A>(Num::Bit0 (Box::new(Num::Bit0 (Box::new(Num::Bit1 (Box::new(Num::One))))))), Box::new(List::Cons (numeral::<A>(Num::Bit1 (Box::new(Num::Bit0 (Box::new(Num::Bit1 (Box::new(Num::One))))))), Box::new(List::Nil))))))
}

pub fn vcga3 () -> Set<(BigInt, Set<BigInt>)> {
    vcga_alg(n3(), omega_3::<BigInt>(), ((Rc::new(move |a: (BigInt, Set<BigInt>)| -> BigInt {
        (*to_function_with_fallback_alg(b3(), BigInt::ZERO))(a.clone())
    })) as Rc<dyn Fn((BigInt, Set<BigInt>)) -> BigInt>), r3::<BigInt>())
}
