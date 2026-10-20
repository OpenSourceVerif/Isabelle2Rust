pub trait Ord {
    fn less_eq (x0: Self, x1: Self) -> bool where Self: Sized;
    fn less (x0: Self, x1: Self) -> bool where Self: Sized;
}

pub trait Preorder : Ord {
    
}

impl<T : Ord> Preorder for T {}

pub trait Order : Preorder {
    
}

impl<T : Preorder> Order for T {}

pub trait Linorder : Order {
    
}

impl<T : Order> Linorder for T {}

pub fn max <A> (a: A, b: A) -> A
where
    A : Clone + Ord + 'static
{
    if <A as Ord>::less_eq(a.clone(), b.clone()) {
        b.clone()
    } else {
        a.clone()
    }
}
