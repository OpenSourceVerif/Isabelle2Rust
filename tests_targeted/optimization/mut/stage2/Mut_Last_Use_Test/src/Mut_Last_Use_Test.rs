#[derive(Clone)]
pub enum LuTree {
    LULeaf(bool),
    LUNode(Box<LuTree>, Box<LuTree>),
}

// borrow-optimized by shared parameters
pub fn lu_flip(x0: &LuTree) -> LuTree {
    match x0 {
        LuTree::LULeaf(b) => {
            LuTree::LULeaf(!b.clone())
        },
        LuTree::LUNode(l, r) => {
            LuTree::LUNode(Box::new(lu_flip(l.as_ref())), Box::new(lu_flip(r.as_ref())))
        },
    }
}

// borrow-optimized by shared parameters
pub fn lu_pair(t: &LuTree) -> crate::Product_Type::Prod<LuTree, LuTree> {
    match t {
        t => {
            crate::Product_Type::Prod::Pair(t.clone(), t.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn lu_wrap(t: &LuTree) -> LuTree {
    match t {
        t => {
            LuTree::LUNode(Box::new(LuTree::LULeaf(true)), Box::new(t.clone()))
        },
    }
}

// borrow-optimized by shared parameters
pub fn lu_pair2(l: &LuTree, r: &LuTree) -> crate::Product_Type::Prod<LuTree, LuTree> {
    match (l.clone(), r.clone()) {
        (l, r) => {
            crate::Product_Type::Prod::Pair(l.clone(), r.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn lu_triple(t: &LuTree) -> crate::Product_Type::Prod<LuTree, crate::Product_Type::Prod<LuTree, LuTree>> {
    match t {
        t => {
            crate::Product_Type::Prod::Pair(t.clone(), crate::Product_Type::Prod::Pair(t.clone(), t.clone()))
        },
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn lu_chain_then_pair(t: &LuTree) -> crate::Product_Type::Prod<LuTree, LuTree> {
    {
        let mut x = t.clone();
        x = lu_wrap(&x);
        x = lu_flip(&x);
        lu_pair(&x)
    }
}

// borrow-optimized by shared parameters
pub fn lu_second_arg_last_use(t: &LuTree) -> crate::Product_Type::Prod<LuTree, LuTree> {
    match t {
        t => {
            lu_pair2(t, t)
        },
    }
}

