#[derive(Clone, Copy)]
pub enum MutWrap <A> {
    MutWrap(A),
}

#[derive(Clone, Copy)]
pub enum MutPairBox <A> {
    MutPairBox(A, A),
}

// borrow-optimized by shared parameters
pub fn wrap_dup<A>(x: &MutWrap<A>) -> crate::Product_Type::Prod<MutWrap<A>, MutWrap<A>> where A: Clone {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(x.clone(), x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn wrap_dup_copy<A>(x: &MutWrap<A>) -> crate::Product_Type::Prod<MutWrap<A>, MutWrap<A>> where A: Copy {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(*x, *x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn wrap_rebuild<A>(x0: &MutWrap<A>) -> MutWrap<A> where A: Clone {
    match x0 {
        MutWrap::MutWrap(x) => {
            MutWrap::MutWrap(x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn wrap_rebuild_copy<A>(x0: &MutWrap<A>) -> MutWrap<A> where A: Copy {
    match x0 {
        MutWrap::MutWrap(x) => {
            MutWrap::MutWrap(*x)
        },
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn wrap_chain<A>(w: &MutWrap<A>) -> MutWrap<A> where A: Clone {
    {
        let mut x = w.clone();
        x = wrap_rebuild(&x);
        x = wrap_rebuild(&x);
        x
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn wrap_chain_copy<A>(w: &MutWrap<A>) -> MutWrap<A> where A: Copy {
    {
        let mut x = *w;
        x = wrap_rebuild_copy(&x);
        x = wrap_rebuild_copy(&x);
        x
    }
}

// borrow-optimized by shared parameters
pub fn pair_box_swap<A>(x0: &MutPairBox<A>) -> MutPairBox<A> where A: Clone {
    match x0 {
        MutPairBox::MutPairBox(x, y) => {
            MutPairBox::MutPairBox(y.clone(), x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn pair_box_swap_copy<A>(x0: &MutPairBox<A>) -> MutPairBox<A> where A: Copy {
    match x0 {
        MutPairBox::MutPairBox(x, y) => {
            MutPairBox::MutPairBox(*y, *x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn pair_box_keep_left<A>(x0: &MutPairBox<A>) -> MutPairBox<A> where A: Clone {
    match x0 {
        MutPairBox::MutPairBox(x, y) => {
            MutPairBox::MutPairBox(x.clone(), x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn pair_box_keep_left_copy<A>(x0: &MutPairBox<A>) -> MutPairBox<A> where A: Copy {
    match x0 {
        MutPairBox::MutPairBox(x, y) => {
            MutPairBox::MutPairBox(*x, *x)
        },
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn pair_box_chain<A>(p: &MutPairBox<A>) -> MutPairBox<A> where A: Clone {
    {
        let mut x = p.clone();
        x = pair_box_swap(&x);
        x = pair_box_keep_left(&x);
        x
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn pair_box_chain_copy<A>(p: &MutPairBox<A>) -> MutPairBox<A> where A: Copy {
    {
        let mut x = *p;
        x = pair_box_swap_copy(&x);
        x = pair_box_keep_left_copy(&x);
        x
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn nested_wrap_chain<A>(w: &MutWrap<MutWrap<A>>) -> MutWrap<MutWrap<A>> where A: Clone {
    {
        let x = w.clone();
        let mut xa = wrap_rebuild(&x);
        xa = wrap_rebuild(&xa);
        xa
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn nested_wrap_chain_copy<A>(w: &MutWrap<MutWrap<A>>) -> MutWrap<MutWrap<A>> where A: Copy {
    {
        let x = *w;
        let mut xa = wrap_rebuild_copy(&x);
        xa = wrap_rebuild_copy(&xa);
        xa
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn wrap_chain_then_dup<A>(w: &MutWrap<A>) -> crate::Product_Type::Prod<MutWrap<A>, MutWrap<A>> where A: Clone {
    {
        let mut x = w.clone();
        x = wrap_rebuild(&x);
        wrap_dup(&x)
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn wrap_chain_then_dup_copy<A>(w: &MutWrap<A>) -> crate::Product_Type::Prod<MutWrap<A>, MutWrap<A>> where A: Copy {
    {
        let mut x = *w;
        x = wrap_rebuild_copy(&x);
        wrap_dup_copy(&x)
    }
}

// borrow-optimized by shared parameters
pub fn wrap_saved_value_blocks_chain<A>(w: &MutWrap<A>) -> crate::Product_Type::Prod<MutWrap<A>, MutWrap<A>> where A: Clone {
    {
        let x = w.clone();
        let saved = x.clone();
        let a = wrap_rebuild(&x);
        crate::Product_Type::Prod::Pair(saved, a)
    }
}

// borrow-optimized by shared parameters
pub fn wrap_saved_value_blocks_chain_copy<A>(w: &MutWrap<A>) -> crate::Product_Type::Prod<MutWrap<A>, MutWrap<A>> where A: Copy {
    {
        let x = *w;
        let saved = x;
        let a = wrap_rebuild_copy(&x);
        crate::Product_Type::Prod::Pair(saved, a)
    }
}

