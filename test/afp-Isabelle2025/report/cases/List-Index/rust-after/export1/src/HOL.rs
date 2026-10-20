pub trait Equal { fn equal(x0 : Self, x1 : Self) -> bool where Self : Sized ; }
pub fn eq<A>(a: A, b: A) -> bool
where
    A: Clone + Equal + 'static
{
    <A as Equal>::equal(a, b)
}

