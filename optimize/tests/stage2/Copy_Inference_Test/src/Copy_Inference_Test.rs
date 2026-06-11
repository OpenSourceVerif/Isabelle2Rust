#[derive(Clone, Copy)]
pub enum Color {
    Red,
    Green,
    Blue,
}

#[derive(Clone, Copy)]
pub enum Pixel {
    Pixel(Color, Color, Color),
}

#[derive(Clone, Copy)]
pub enum Palette {
    Palette(Pixel, Pixel),
}

#[derive(Clone)]
pub enum CopyTree {
    CopyLeaf(bool),
    CopyNode(Box<CopyTree>, Box<CopyTree>),
}

#[derive(Clone, Copy)]
pub enum CopyWrap <A> {
    CopyWrap(A),
}

#[derive(Clone, Copy)]
pub enum FlagPair {
    FlagPair(bool, bool),
}

#[derive(Clone, Copy)]
pub enum FlagTriple {
    FlagTriple(bool, bool, bool),
}

#[derive(Clone, Copy)]
pub enum NestedPair {
    NestedPair(FlagPair, Color),
}

#[derive(Clone, Copy)]
pub enum CopyPairWrap <A, B> {
    CopyPairWrap(A, B),
}

#[derive(Clone, Copy)]
pub enum NestedCopyWrap <A> {
    NestedCopyWrap(CopyWrap<A>),
}

// borrow-optimized by shared parameters
pub fn flag_dup(x: &FlagPair) -> crate::Product_Type::Prod<FlagPair, FlagPair> {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(*x, *x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn tree_dup(x: &CopyTree) -> crate::Product_Type::Prod<CopyTree, CopyTree> {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(x.clone(), x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn wrap_dup<A>(x: &CopyWrap<A>) -> crate::Product_Type::Prod<CopyWrap<A>, CopyWrap<A>> where A: Clone {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(x.clone(), x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn wrap_dup_copy<A>(x: &CopyWrap<A>) -> crate::Product_Type::Prod<CopyWrap<A>, CopyWrap<A>> where A: Copy {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(*x, *x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn color_dup(c: &Color) -> crate::Product_Type::Prod<Color, Color> {
    match c {
        c => {
            crate::Product_Type::Prod::Pair(*c, *c)
        },
    }
}

// borrow-optimized by shared parameters
pub fn flag_left(x0: &FlagPair) -> bool {
    match x0 {
        FlagPair::FlagPair(x, y) => {
            *x
        },
    }
}

// borrow-optimized by shared parameters
pub fn flag_swap(x0: &FlagPair) -> FlagPair {
    match x0 {
        FlagPair::FlagPair(x, y) => {
            FlagPair::FlagPair(*y, *x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn value_dup<A>(x: &A) -> crate::Product_Type::Prod<A, A> where A: Clone {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(x.clone(), x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn value_dup_copy<A>(x: &A) -> crate::Product_Type::Prod<A, A> where A: Copy {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(*x, *x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn flag_right(x0: &FlagPair) -> bool {
    match x0 {
        FlagPair::FlagPair(x, y) => {
            *y
        },
    }
}

// borrow-optimized by shared parameters
pub fn nested_dup(x: &NestedPair) -> crate::Product_Type::Prod<NestedPair, NestedPair> {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(*x, *x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn pixel_first(x0: &Pixel) -> Color {
    match x0 {
        Pixel::Pixel(r, g, b) => {
            *r
        },
    }
}

// borrow-optimized by shared parameters
pub fn wrap_unwrap<A>(x0: &CopyWrap<A>) -> A where A: Clone {
    match x0 {
        CopyWrap::CopyWrap(x) => {
            x.clone()
        },
    }
}

// borrow-optimized by shared parameters
pub fn wrap_unwrap_copy<A>(x0: &CopyWrap<A>) -> A where A: Copy {
    match x0 {
        CopyWrap::CopyWrap(x) => {
            *x
        },
    }
}

// borrow-optimized by shared parameters
pub fn color_is_red(x0: &Color) -> bool {
    match x0 {
        Color::Red => {
            true
        },
        Color::Green => {
            false
        },
        Color::Blue => {
            false
        },
    }
}

// borrow-optimized by shared parameters
pub fn palette_swap(x0: &Palette) -> Palette {
    match x0 {
        Palette::Palette(p, q) => {
            Palette::Palette(*q, *p)
        },
    }
}

// borrow-optimized by shared parameters
pub fn pixel_rotate(x0: &Pixel) -> Pixel {
    match x0 {
        Pixel::Pixel(r, g, b) => {
            Pixel::Pixel(*g, *b, *r)
        },
    }
}

// borrow-optimized by shared parameters
pub fn pixel_second(x0: &Pixel) -> Color {
    match x0 {
        Pixel::Pixel(r, g, b) => {
            *g
        },
    }
}

// borrow-optimized by shared parameters
pub fn tree_is_leaf(x0: &CopyTree) -> bool {
    match x0 {
        CopyTree::CopyLeaf(b) => {
            true
        },
        CopyTree::CopyNode(l, r) => {
            false
        },
    }
}

// borrow-optimized by shared parameters
pub fn triple_first(x0: &FlagTriple) -> bool {
    match x0 {
        FlagTriple::FlagTriple(x, y, z) => {
            *x
        },
    }
}

// borrow-optimized by shared parameters
pub fn pair_wrap_dup<B, A>(x: &CopyPairWrap<A, B>) -> crate::Product_Type::Prod<CopyPairWrap<A, B>, CopyPairWrap<A, B>> where B: Clone, A: Clone {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(x.clone(), x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn pair_wrap_dup_copy<B, A>(x: &CopyPairWrap<A, B>) -> crate::Product_Type::Prod<CopyPairWrap<A, B>, CopyPairWrap<A, B>> where B: Copy, A: Copy {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(*x, *x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn palette_first(x0: &Palette) -> Pixel {
    match x0 {
        Palette::Palette(p, q) => {
            *p
        },
    }
}

// borrow-optimized by shared parameters
pub fn triple_rotate(x0: &FlagTriple) -> FlagTriple {
    match x0 {
        FlagTriple::FlagTriple(x, y, z) => {
            FlagTriple::FlagTriple(*y, *z, *x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn triple_second(x0: &FlagTriple) -> bool {
    match x0 {
        FlagTriple::FlagTriple(x, y, z) => {
            *y
        },
    }
}

// borrow-optimized by shared parameters
pub fn wrap_map_flag(x0: &CopyWrap<FlagPair>) -> FlagPair {
    match x0 {
        CopyWrap::CopyWrap(x) => {
            *x
        },
    }
}

// borrow-optimized by shared parameters
pub fn wrap_tree_dup(x: &CopyWrap<CopyTree>) -> crate::Product_Type::Prod<CopyWrap<CopyTree>, CopyWrap<CopyTree>> {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(x.clone(), x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn mixed_pair_dup(x: &CopyPairWrap<FlagPair, CopyTree>) -> crate::Product_Type::Prod<CopyPairWrap<FlagPair, CopyTree>, CopyPairWrap<FlagPair, CopyTree>> {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(x.clone(), x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn pair_wrap_swap<A, B>(x0: &CopyPairWrap<A, B>) -> CopyPairWrap<B, A> where A: Clone, B: Clone {
    match x0 {
        CopyPairWrap::CopyPairWrap(x, y) => {
            CopyPairWrap::CopyPairWrap(y.clone(), x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn pair_wrap_swap_copy<A, B>(x0: &CopyPairWrap<A, B>) -> CopyPairWrap<B, A> where A: Copy, B: Copy {
    match x0 {
        CopyPairWrap::CopyPairWrap(x, y) => {
            CopyPairWrap::CopyPairWrap(*y, *x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn nested_get_flag(x0: &NestedPair) -> FlagPair {
    match x0 {
        NestedPair::NestedPair(p, c) => {
            *p
        },
    }
}

// borrow-optimized by shared parameters
pub fn nested_wrap_dup<A>(x: &NestedCopyWrap<A>) -> crate::Product_Type::Prod<NestedCopyWrap<A>, NestedCopyWrap<A>> where A: Clone {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(x.clone(), x.clone())
        },
    }
}

// borrow-optimized by shared parameters
pub fn nested_wrap_dup_copy<A>(x: &NestedCopyWrap<A>) -> crate::Product_Type::Prod<NestedCopyWrap<A>, NestedCopyWrap<A>> where A: Copy {
    match x {
        x => {
            crate::Product_Type::Prod::Pair(*x, *x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn pair_wrap_first<A, B>(x0: &CopyPairWrap<A, B>) -> A where A: Clone, B: Clone {
    match x0 {
        CopyPairWrap::CopyPairWrap(x, y) => {
            x.clone()
        },
    }
}

// borrow-optimized by shared parameters
pub fn pair_wrap_first_copy<A, B>(x0: &CopyPairWrap<A, B>) -> A where A: Copy, B: Clone {
    match x0 {
        CopyPairWrap::CopyPairWrap(x, y) => {
            *x
        },
    }
}

// borrow-optimized by shared parameters
pub fn mixed_pair_first(x0: &CopyPairWrap<FlagPair, CopyTree>) -> FlagPair {
    match x0 {
        CopyPairWrap::CopyPairWrap(x, t) => {
            *x
        },
    }
}

// borrow-optimized by shared parameters
pub fn nested_get_color(x0: &NestedPair) -> Color {
    match x0 {
        NestedPair::NestedPair(p, c) => {
            *c
        },
    }
}

// borrow-optimized by shared parameters
pub fn use_wrap_dup_flag(x: &CopyWrap<FlagPair>) -> crate::Product_Type::Prod<CopyWrap<FlagPair>, CopyWrap<FlagPair>> {
    match x {
        x => {
            wrap_dup_copy(x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn use_value_dup_flag(x: &FlagPair) -> crate::Product_Type::Prod<FlagPair, FlagPair> {
    match x {
        x => {
            value_dup_copy(x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn pixel_replace_first(x0: &Pixel, c: &Color) -> Pixel {
    match (*x0, *c) {
        (Pixel::Pixel(r, g, b), c) => {
            Pixel::Pixel(c, g, b)
        },
    }
}

// borrow-optimized by shared parameters
pub fn use_wrap_dup_generic<A>(x: &CopyWrap<A>) -> crate::Product_Type::Prod<CopyWrap<A>, CopyWrap<A>> where A: Clone {
    match x {
        x => {
            wrap_dup(x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn use_wrap_dup_generic_copy<A>(x: &CopyWrap<A>) -> crate::Product_Type::Prod<CopyWrap<A>, CopyWrap<A>> where A: Copy {
    match x {
        x => {
            wrap_dup_copy(x)
        },
    }
}

// borrow-optimized by shared parameters
pub fn nested_wrap_unwrap_flag(x0: &NestedCopyWrap<FlagPair>) -> FlagPair {
    match x0 {
        NestedCopyWrap::NestedCopyWrap(CopyWrap::CopyWrap(x)) => {
            *x
        },
    }
}

