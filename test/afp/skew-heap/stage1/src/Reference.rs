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

#[derive(Clone)]
pub enum Tree<A> {
    Leaf,
    Node (Box<Tree<A>>, A, Box<Tree<A>>)
}

pub fn merge <A> (t: Tree<A>, ta: Tree<A>) -> Tree<A>
where
    A : Clone + Linorder + 'static
{
    match (t, ta) {
        (Tree::Leaf, t) =>
            t.clone(),
        (t, Tree::Leaf) =>
            t.clone(),
        (Tree::Node (p0, a1, p1), Tree::Node (p2, a2, p3)) =>
            {
                let l1 = *p0;
                let r1 = *p1;
                let l2 = *p2;
                let r2 = *p3;
                {
                    let t2 = Tree::Node (Box::new(l2.clone()), a2.clone(), Box::new(r2.clone()));
                    let t1 = Tree::Node (Box::new(l1.clone()), a1.clone(), Box::new(r1.clone()));
                    if <A as Ord>::less_eq(a1.clone(), a2.clone()) {
                        Tree::Node (Box::new(merge(t2.clone(), r1.clone())), a1.clone(), Box::new(l1.clone()))
                    } else {
                        Tree::Node (Box::new(merge(t1.clone(), r2.clone())), a2.clone(), Box::new(l2.clone()))
                    }
                }
            },
        _ =>
            panic!("non-exhaustive match")
    }
}
