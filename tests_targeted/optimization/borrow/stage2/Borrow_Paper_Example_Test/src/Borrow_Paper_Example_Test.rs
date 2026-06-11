#[derive(Clone)]
pub enum Tree {
    Leaf(bool),
    Branch(Box<Tree>, Box<Tree>),
}

// borrow-optimized by shared parameters
pub fn rebuild(x0: &Tree) -> Tree {
    match x0 {
        Tree::Leaf(b) => {
            Tree::Leaf(*b)
        },
        Tree::Branch(l, r) => {
            Tree::Branch(Box::new(rebuild(l.as_ref())), Box::new(rebuild(r.as_ref())))
        },
    }
}

// borrow-optimized by shared parameters
pub fn any_label(x0: &Tree) -> bool {
    match x0 {
        Tree::Leaf(b) => {
            *b
        },
        Tree::Branch(l, r) => {
            any_label(l.as_ref()) || any_label(r.as_ref())
        },
    }
}

// borrow-optimized by shared parameters
pub fn any_label_twice(t: &Tree) -> bool {
    any_label(t) && any_label(t)
}

