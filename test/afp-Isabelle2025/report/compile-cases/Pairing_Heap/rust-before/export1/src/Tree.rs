use crate::HOL::Equal;
use crate::HOL::eq;
use crate::Set::Set;
use crate::Set::bot_set;
use crate::Set::insert;
use crate::Set::sup_set;

#[derive(Clone)]
pub enum Tree<A> {
    Leaf,
    Node (Box<Tree<A>>, A, Box<Tree<A>>)
}

pub fn set_tree <A> (x0: Tree<A>) -> Set<A>
where
    A : Clone + Equal + 'static
{
    match x0 {
        Tree::Leaf =>
            bot_set::<A>(),
        Tree::Node (p0, x22, p1) =>
            {
                let x21 = *p0;
                let x23 = *p1;
                sup_set(sup_set(set_tree(x21.clone()), insert(x22.clone(), bot_set::<A>())), set_tree(x23.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

impl <A : Clone + Equal + 'static> Equal for Tree<A> {
    fn equal (x0: Tree<A>, x1: Tree<A>) -> bool {
        match (x0, x1) {
            (Tree::Leaf, Tree::Node (_, _, _)) =>
                false,
            (Tree::Node (_, _, _), Tree::Leaf) =>
                false,
            (Tree::Node (p0, x22, p1), Tree::Node (p2, y22, p3)) =>
                {
                    let x21 = *p0;
                    let x23 = *p1;
                    let y21 = *p2;
                    let y23 = *p3;
                    <Tree<A> as Equal>::equal(x21.clone(), y21.clone()) &&
                      (eq(x22.clone(), y22.clone()) &&
                        <Tree<A> as Equal>::equal(x23.clone(), y23.clone()))
                },
            (Tree::Leaf, Tree::Leaf) =>
                true,
            _ =>
                panic!("non-exhaustive match")
        }
    }
}
