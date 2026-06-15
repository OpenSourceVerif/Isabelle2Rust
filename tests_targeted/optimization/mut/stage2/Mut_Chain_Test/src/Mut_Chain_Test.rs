#[derive(Clone)]
pub enum Peano {
    Za,
    S(Box<Peano>),
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn grow(n: &Peano) -> Peano {
    {
        let mut x = n.clone();
        x = Peano::S(Box::new(x));
        x = Peano::S(Box::new(x));
        x
    }
}

