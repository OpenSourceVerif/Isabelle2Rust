pub enum Tree<T> {
    Leaf,
    Node(Box<Tree<T>>, T, Box<Tree<T>>),
}

pub fn merge<T: Ord>(a: Tree<T>, b: Tree<T>) -> Tree<T> {
    match a {
        Tree::Leaf => b,
        Tree::Node(l1, a1, r1) => match b {
            Tree::Leaf => Tree::Node(l1, a1, r1),
            Tree::Node(l2, a2, r2) => {
                if a1 <= a2 {
                    let t2 = Tree::Node(l2, a2, r2);
                    Tree::Node(Box::new(merge(t2, *r1)), a1, l1)
                } else {
                    let t1 = Tree::Node(l1, a1, r1);
                    Tree::Node(Box::new(merge(t1, *r2)), a2, l2)
                }
            }
        },
    }
}
