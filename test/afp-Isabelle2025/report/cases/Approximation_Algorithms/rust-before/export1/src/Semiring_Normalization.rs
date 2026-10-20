use crate::Rings::CommSemiring1Cancel;

pub trait CommSemiring1CancelCrossproduct : CommSemiring1Cancel {
    
}

impl<T : CommSemiring1Cancel> CommSemiring1CancelCrossproduct for T {}
