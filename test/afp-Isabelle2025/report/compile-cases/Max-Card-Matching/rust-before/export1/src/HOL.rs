pub trait Equal {
    fn equal (x0: Self, x1: Self) -> bool where Self: Sized;
}

pub fn eq <A> (a: A, b: A) -> bool
where
    A : Clone + Equal + 'static
{
    <A as Equal>::equal(a.clone(), b.clone())
}

pub fn implies (p: bool, pa: bool) -> bool {
    match (p, pa) {
        (_, true) =>
            true,
        (p, false) =>
            ! p.clone(),
        (true, p) =>
            p.clone(),
        (false, _) =>
            true,
        _ =>
            panic!("non-exhaustive match")
    }
}
