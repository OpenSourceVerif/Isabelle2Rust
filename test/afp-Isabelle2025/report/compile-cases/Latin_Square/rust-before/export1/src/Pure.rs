use std::marker::PhantomData;

#[derive(Clone)]
pub enum Itself<A> {
    Type (PhantomData<A>)
}
