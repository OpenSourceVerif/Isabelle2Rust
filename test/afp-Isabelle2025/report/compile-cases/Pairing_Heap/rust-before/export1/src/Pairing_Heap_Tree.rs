use crate::HOL::Equal;
use crate::Orderings::Linorder;
use crate::Orderings::Ord;
use crate::Set::Set;
use crate::Set::ball;
use crate::Tree::Tree;
use crate::Tree::set_tree;

use std::rc::Rc;

pub fn link <A> (x0: Tree<A>) -> Tree<A>
where
    A : Clone + Linorder + 'static
{
    match x0 {
        Tree::Node (p0, p0a, p0b) =>
            match *p0b {
                Tree::Node (p1, y, p1b) =>
                    {
                        let hsx = *p0;
                        let x = p0a;
                        let hsy = *p1;
                        let hs = *p1b;
                        if <A as Ord>::less(x.clone(), y.clone()) {
                            Tree::Node (Box::new(Tree::Node (Box::new(hsy.clone()), y.clone(), Box::new(hsx.clone()))), x.clone(), Box::new(hs.clone()))
                        } else {
                            Tree::Node (Box::new(Tree::Node (Box::new(hsx.clone()), x.clone(), Box::new(hsy.clone()))), y.clone(), Box::new(hs.clone()))
                        }
                    },
                Tree::Leaf =>
                    {
                        let v = *p0;
                        let va = p0a;
                        Tree::Node (Box::new(v.clone()), va.clone(), Box::new(Tree::Leaf))
                    },
                _ =>
                    panic!("non-exhaustive match")
            },
        Tree::Leaf =>
            Tree::Leaf,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn merge <A> (x0: Tree<A>, hp: Tree<A>) -> Tree<A>
where
    A : Clone + Linorder + 'static
{
    match (x0, hp) {
        (Tree::Leaf, hp) =>
            hp.clone(),
        (Tree::Node (p0, va, p1), Tree::Leaf) =>
            {
                let v = *p0;
                let vb = *p1;
                Tree::Node (Box::new(v.clone()), va.clone(), Box::new(vb.clone()))
            },
        (Tree::Node (p0, x, _), Tree::Node (p1, y, _)) =>
            {
                let hsx = *p0;
                let hsy = *p1;
                link(Tree::Node (Box::new(hsx.clone()), x.clone(), Box::new(Tree::Node (Box::new(hsy.clone()), y.clone(), Box::new(Tree::Leaf)))))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn pheap <A> (x0: Tree<A>) -> bool
where
    A : Clone + Equal + Linorder + 'static
{
    match x0 {
        Tree::Leaf =>
            true,
        Tree::Node (p0, x, p1) =>
            {
                let l = *p0;
                let r = *p1;
                ball(set_tree(l.clone()), (({
                      let x_cap = x.clone();
                      Rc::new(move |a: A| -> bool {
                          <A as Ord>::less_eq(x_cap.clone(), a.clone())
                      })
                  }) as Rc<dyn Fn(A) -> bool>)) &&
                  (pheap(l.clone()) && pheap(r.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn insert <A> (x: A, hp: Tree<A>) -> Tree<A>
where
    A : Clone + Linorder + 'static
{
    merge(Tree::Node (Box::new(Tree::Leaf), x.clone(), Box::new(Tree::Leaf)), hp.clone())
}

pub fn pass_2 <A> (x0: Tree<A>) -> Tree<A>
where
    A : Clone + Linorder + 'static
{
    match x0 {
        Tree::Node (p0, x, p1) =>
            {
                let hsx = *p0;
                let hs = *p1;
                link(Tree::Node (Box::new(hsx.clone()), x.clone(), Box::new(pass_2(hs.clone()))))
            },
        Tree::Leaf =>
            Tree::Leaf,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn pass_1 <A> (x0: Tree<A>) -> Tree<A>
where
    A : Clone + Linorder + 'static
{
    match x0 {
        Tree::Node (p0, p0a, p0b) =>
            match *p0b {
                Tree::Node (p1, y, p1b) =>
                    {
                        let hsx = *p0;
                        let x = p0a;
                        let hsy = *p1;
                        let hs = *p1b;
                        link(Tree::Node (Box::new(hsx.clone()), x.clone(), Box::new(Tree::Node (Box::new(hsy.clone()), y.clone(), Box::new(pass_1(hs.clone()))))))
                    },
                Tree::Leaf =>
                    {
                        let v = *p0;
                        let va = p0a;
                        Tree::Node (Box::new(v.clone()), va.clone(), Box::new(Tree::Leaf))
                    },
                _ =>
                    panic!("non-exhaustive match")
            },
        Tree::Leaf =>
            Tree::Leaf,
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn del_min <A> (x0: Tree<A>) -> Tree<A>
where
    A : Clone + Linorder + 'static
{
    match x0 {
        Tree::Leaf =>
            Tree::Leaf,
        Tree::Node (p0, _, _) =>
            {
                let hs = *p0;
                pass_2(pass_1(hs.clone()))
            },
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn get_min <A> (x0: Tree<A>) -> A
where
    A : Clone + Linorder + 'static
{
    match x0 {
        Tree::Node (_, x, _) =>
            x.clone(),
        _ =>
            panic!("non-exhaustive match")
    }
}

pub fn is_root <A> (hp: Tree<A>) -> bool
where
    A : Clone + Equal + 'static
{
    match hp.clone() {
        Tree::Leaf =>
            true,
        Tree::Node (_, _, p0) =>
            {
                let r = *p0;
                <Tree<A> as Equal>::equal(r.clone(), Tree::Leaf)
            },
        _ =>
            panic!("non-exhaustive match")
    }
}
