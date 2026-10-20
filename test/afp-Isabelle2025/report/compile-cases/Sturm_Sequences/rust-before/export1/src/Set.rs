use crate::List::List;

#[derive(Clone)]
pub enum Set<A> {
    Set (List<A>),
    Coset (List<A>)
}
