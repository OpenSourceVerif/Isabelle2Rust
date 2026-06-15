#[derive(Clone)]
pub enum MutTree {
    MTLeaf(bool),
    MTNode(Box<MutTree>, Box<MutTree>),
}

// borrow-optimized by shared parameters
pub fn mtree_mirror(x0: &MutTree) -> MutTree {
    match x0 {
        MutTree::MTLeaf(b) => {
            MutTree::MTLeaf(*b)
        },
        MutTree::MTNode(l, r) => {
            MutTree::MTNode(Box::new(mtree_mirror(r.as_ref())), Box::new(mtree_mirror(l.as_ref())))
        },
    }
}

// borrow-optimized by shared parameters
pub fn mtree_set_all(b: &bool, x1: &MutTree) -> MutTree {
    match (*b, x1.clone()) {
        (b, MutTree::MTLeaf(uu)) => {
            MutTree::MTLeaf(b)
        },
        (b, MutTree::MTNode(box l, box r)) => {
            MutTree::MTNode(Box::new(mtree_set_all(&b, &l.clone())), Box::new(mtree_set_all(&b, &r.clone())))
        },
    }
}

// borrow-optimized by shared parameters
pub fn mtree_any_label(x0: &MutTree) -> bool {
    match x0 {
        MutTree::MTLeaf(b) => {
            *b
        },
        MutTree::MTNode(l, r) => {
            mtree_any_label(l.as_ref()) || mtree_any_label(r.as_ref())
        },
    }
}

// borrow-optimized by shared parameters
pub fn mtree_flip_labels(x0: &MutTree) -> MutTree {
    match x0 {
        MutTree::MTLeaf(b) => {
            MutTree::MTLeaf(!b.clone())
        },
        MutTree::MTNode(l, r) => {
            MutTree::MTNode(Box::new(mtree_flip_labels(l.as_ref())), Box::new(mtree_flip_labels(r.as_ref())))
        },
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn mtree_two_chains(t: &MutTree, u: &MutTree) -> MutTree {
    {
        let mut x = t.clone();
        let mut y = u.clone();
        x = mtree_mirror(&x);
        y = mtree_flip_labels(&y);
        MutTree::MTNode(Box::new(x), Box::new(y))
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn mtree_rebuild_chain(t: &MutTree) -> MutTree {
    {
        let mut x = t.clone();
        x = mtree_flip_labels(&x);
        x = mtree_mirror(&x);
        x = mtree_set_all(&true, &x);
        x
    }
}

// borrow-optimized by shared parameters
pub fn mtree_branch_rhs_chain(flag: &bool, t: &MutTree) -> MutTree {
    {
        let x = t.clone();
        let xa = match flag {
            true => {
                mtree_mirror(&x)
            },
            false => {
                mtree_flip_labels(&x)
            },
        };
        let xb = mtree_set_all(flag, &xa.clone());
        xb
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn mtree_interleaved_chain(seed: &bool, t: &MutTree) -> MutTree {
    {
        let mut x = t.clone();
        let mark = *seed;
        x = mtree_set_all(&mark, &x);
        let marka = !mark.clone();
        x = mtree_set_all(&marka.clone(), &mtree_mirror(&x));
        x
    }
}

// borrow-optimized by shared parameters
pub fn mtree_saved_value_blocks_chain(t: &MutTree) -> MutTree {
    {
        let x = t.clone();
        let saved = x.clone();
        let a = mtree_mirror(&x);
        MutTree::MTNode(Box::new(saved), Box::new(a))
    }
}

