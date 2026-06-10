use num_bigint::*;
use num_traits::sign::*;
use crate::Product_Type::*;
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

pub fn flag_dup(x: FlagPair) -> Prod<FlagPair, FlagPair> {
    match x {
        x => {
            Prod::Pair(x, x)
        },
    }
}

pub fn flag_dup_borrow(x: &FlagPair) -> Prod<FlagPair, FlagPair> {
    match x {
        x => {
            Prod::Pair(*x, *x)
        },
    }
}

pub fn tree_dup(x: CopyTree) -> Prod<CopyTree, CopyTree> {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn tree_dup_borrow(x: &CopyTree) -> Prod<CopyTree, CopyTree> {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn wrap_dup<A>(x: CopyWrap<A>) -> Prod<CopyWrap<A>, CopyWrap<A>> where A: Clone {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn wrap_dup_borrow<A>(x: &CopyWrap<A>) -> Prod<CopyWrap<A>, CopyWrap<A>> where A: Clone {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn color_dup(c: Color) -> Prod<Color, Color> {
    match c {
        c => {
            Prod::Pair(c, c)
        },
    }
}

pub fn color_dup_borrow(c: &Color) -> Prod<Color, Color> {
    match c {
        c => {
            Prod::Pair(*c, *c)
        },
    }
}

pub fn flag_left(x0: FlagPair) -> bool {
    match x0 {
        FlagPair::FlagPair(x, y) => {
            x
        },
    }
}

pub fn flag_left_borrow(x0: &FlagPair) -> bool {
    match x0 {
        FlagPair::FlagPair(x, y) => {
            *x
        },
    }
}

pub fn flag_swap(x0: FlagPair) -> FlagPair {
    match x0 {
        FlagPair::FlagPair(x, y) => {
            FlagPair::FlagPair(y, x)
        },
    }
}

pub fn flag_swap_borrow(x0: &FlagPair) -> FlagPair {
    match x0 {
        FlagPair::FlagPair(x, y) => {
            FlagPair::FlagPair(*y, *x)
        },
    }
}

pub fn value_dup<A>(x: A) -> Prod<A, A> where A: Clone {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn value_dup_borrow<A>(x: &A) -> Prod<A, A> where A: Clone {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn flag_right(x0: FlagPair) -> bool {
    match x0 {
        FlagPair::FlagPair(x, y) => {
            y
        },
    }
}

pub fn flag_right_borrow(x0: &FlagPair) -> bool {
    match x0 {
        FlagPair::FlagPair(x, y) => {
            *y
        },
    }
}

pub fn nested_dup(x: NestedPair) -> Prod<NestedPair, NestedPair> {
    match x {
        x => {
            Prod::Pair(x, x)
        },
    }
}

pub fn nested_dup_borrow(x: &NestedPair) -> Prod<NestedPair, NestedPair> {
    match x {
        x => {
            Prod::Pair(*x, *x)
        },
    }
}

pub fn pixel_first(x0: Pixel) -> Color {
    match x0 {
        Pixel::Pixel(r, g, b) => {
            r
        },
    }
}

pub fn pixel_first_borrow(x0: &Pixel) -> Color {
    match x0 {
        Pixel::Pixel(r, g, b) => {
            *r
        },
    }
}

pub fn wrap_unwrap<A>(x0: CopyWrap<A>) -> A where A: Clone {
    match x0 {
        CopyWrap::CopyWrap(x) => {
            x.clone()
        },
    }
}

pub fn wrap_unwrap_borrow<A>(x0: &CopyWrap<A>) -> A where A: Clone {
    match x0 {
        CopyWrap::CopyWrap(x) => {
            x.clone()
        },
    }
}

pub fn color_is_red(x0: Color) -> bool {
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

pub fn color_is_red_borrow(x0: &Color) -> bool {
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

pub fn palette_swap(x0: Palette) -> Palette {
    match x0 {
        Palette::Palette(p, q) => {
            Palette::Palette(q, p)
        },
    }
}

pub fn palette_swap_borrow(x0: &Palette) -> Palette {
    match x0 {
        Palette::Palette(p, q) => {
            Palette::Palette(*q, *p)
        },
    }
}

pub fn pixel_rotate(x0: Pixel) -> Pixel {
    match x0 {
        Pixel::Pixel(r, g, b) => {
            Pixel::Pixel(g, b, r)
        },
    }
}

pub fn pixel_rotate_borrow(x0: &Pixel) -> Pixel {
    match x0 {
        Pixel::Pixel(r, g, b) => {
            Pixel::Pixel(*g, *b, *r)
        },
    }
}

pub fn pixel_second(x0: Pixel) -> Color {
    match x0 {
        Pixel::Pixel(r, g, b) => {
            g
        },
    }
}

pub fn pixel_second_borrow(x0: &Pixel) -> Color {
    match x0 {
        Pixel::Pixel(r, g, b) => {
            *g
        },
    }
}

pub fn tree_is_leaf(x0: CopyTree) -> bool {
    match x0 {
        CopyTree::CopyLeaf(b) => {
            true
        },
        CopyTree::CopyNode(box l, box r) => {
            false
        },
    }
}

pub fn tree_is_leaf_borrow(x0: &CopyTree) -> bool {
    match x0 {
        CopyTree::CopyLeaf(b) => {
            true
        },
        CopyTree::CopyNode(l, r) => {
            false
        },
    }
}

pub fn triple_first(x0: FlagTriple) -> bool {
    match x0 {
        FlagTriple::FlagTriple(x, y, z) => {
            x
        },
    }
}

pub fn triple_first_borrow(x0: &FlagTriple) -> bool {
    match x0 {
        FlagTriple::FlagTriple(x, y, z) => {
            *x
        },
    }
}

pub fn pair_wrap_dup<A, B>(x: CopyPairWrap<A, B>) -> Prod<CopyPairWrap<A, B>, CopyPairWrap<A, B>> where A: Clone, B: Clone {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn pair_wrap_dup_borrow<A, B>(x: &CopyPairWrap<A, B>) -> Prod<CopyPairWrap<A, B>, CopyPairWrap<A, B>> where A: Clone, B: Clone {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn palette_first(x0: Palette) -> Pixel {
    match x0 {
        Palette::Palette(p, q) => {
            p
        },
    }
}

pub fn palette_first_borrow(x0: &Palette) -> Pixel {
    match x0 {
        Palette::Palette(p, q) => {
            *p
        },
    }
}

pub fn triple_rotate(x0: FlagTriple) -> FlagTriple {
    match x0 {
        FlagTriple::FlagTriple(x, y, z) => {
            FlagTriple::FlagTriple(y, z, x)
        },
    }
}

pub fn triple_rotate_borrow(x0: &FlagTriple) -> FlagTriple {
    match x0 {
        FlagTriple::FlagTriple(x, y, z) => {
            FlagTriple::FlagTriple(*y, *z, *x)
        },
    }
}

pub fn triple_second(x0: FlagTriple) -> bool {
    match x0 {
        FlagTriple::FlagTriple(x, y, z) => {
            y
        },
    }
}

pub fn triple_second_borrow(x0: &FlagTriple) -> bool {
    match x0 {
        FlagTriple::FlagTriple(x, y, z) => {
            *y
        },
    }
}

pub fn wrap_map_flag(x0: CopyWrap<FlagPair>) -> FlagPair {
    match x0 {
        CopyWrap::CopyWrap(x) => {
            x
        },
    }
}

pub fn wrap_map_flag_borrow(x0: &CopyWrap<FlagPair>) -> FlagPair {
    match x0 {
        CopyWrap::CopyWrap(x) => {
            *x
        },
    }
}

pub fn wrap_tree_dup(x: CopyWrap<CopyTree>) -> Prod<CopyWrap<CopyTree>, CopyWrap<CopyTree>> {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn wrap_tree_dup_borrow(x: &CopyWrap<CopyTree>) -> Prod<CopyWrap<CopyTree>, CopyWrap<CopyTree>> {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn mixed_pair_dup(x: CopyPairWrap<FlagPair, CopyTree>) -> Prod<CopyPairWrap<FlagPair, CopyTree>, CopyPairWrap<FlagPair, CopyTree>> {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn mixed_pair_dup_borrow(x: &CopyPairWrap<FlagPair, CopyTree>) -> Prod<CopyPairWrap<FlagPair, CopyTree>, CopyPairWrap<FlagPair, CopyTree>> {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn pair_wrap_swap<A, B>(x0: CopyPairWrap<A, B>) -> CopyPairWrap<B, A> where A: Clone, B: Clone {
    match x0 {
        CopyPairWrap::CopyPairWrap(x, y) => {
            CopyPairWrap::CopyPairWrap(y.clone(), x.clone())
        },
    }
}

pub fn pair_wrap_swap_borrow<A, B>(x0: &CopyPairWrap<A, B>) -> CopyPairWrap<B, A> where A: Clone, B: Clone {
    match x0 {
        CopyPairWrap::CopyPairWrap(x, y) => {
            CopyPairWrap::CopyPairWrap(y.clone(), x.clone())
        },
    }
}

pub fn nested_get_flag(x0: NestedPair) -> FlagPair {
    match x0 {
        NestedPair::NestedPair(p, c) => {
            p
        },
    }
}

pub fn nested_get_flag_borrow(x0: &NestedPair) -> FlagPair {
    match x0 {
        NestedPair::NestedPair(p, c) => {
            *p
        },
    }
}

pub fn nested_wrap_dup<A>(x: NestedCopyWrap<A>) -> Prod<NestedCopyWrap<A>, NestedCopyWrap<A>> where A: Clone {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn nested_wrap_dup_borrow<A>(x: &NestedCopyWrap<A>) -> Prod<NestedCopyWrap<A>, NestedCopyWrap<A>> where A: Clone {
    match x {
        x => {
            Prod::Pair(x.clone(), x.clone())
        },
    }
}

pub fn pair_wrap_first<A, B>(x0: CopyPairWrap<A, B>) -> A where A: Clone, B: Clone {
    match x0 {
        CopyPairWrap::CopyPairWrap(x, y) => {
            x.clone()
        },
    }
}

pub fn pair_wrap_first_borrow<A, B>(x0: &CopyPairWrap<A, B>) -> A where A: Clone, B: Clone {
    match x0 {
        CopyPairWrap::CopyPairWrap(x, y) => {
            x.clone()
        },
    }
}

pub fn mixed_pair_first(x0: CopyPairWrap<FlagPair, CopyTree>) -> FlagPair {
    match x0 {
        CopyPairWrap::CopyPairWrap(x, t) => {
            x
        },
    }
}

pub fn mixed_pair_first_borrow(x0: &CopyPairWrap<FlagPair, CopyTree>) -> FlagPair {
    match x0 {
        CopyPairWrap::CopyPairWrap(x, t) => {
            *x
        },
    }
}

pub fn nested_get_color(x0: NestedPair) -> Color {
    match x0 {
        NestedPair::NestedPair(p, c) => {
            c
        },
    }
}

pub fn nested_get_color_borrow(x0: &NestedPair) -> Color {
    match x0 {
        NestedPair::NestedPair(p, c) => {
            *c
        },
    }
}

pub fn use_wrap_dup_flag(x: CopyWrap<FlagPair>) -> Prod<CopyWrap<FlagPair>, CopyWrap<FlagPair>> {
    match x {
        x => {
            wrap_dup_copy(x)
        },
    }
}

pub fn use_wrap_dup_flag_borrow(x: &CopyWrap<FlagPair>) -> Prod<CopyWrap<FlagPair>, CopyWrap<FlagPair>> {
    match x {
        x => {
            wrap_dup_copy(*x)
        },
    }
}

pub fn use_value_dup_flag(x: FlagPair) -> Prod<FlagPair, FlagPair> {
    match x {
        x => {
            value_dup_copy(x)
        },
    }
}

pub fn use_value_dup_flag_borrow(x: &FlagPair) -> Prod<FlagPair, FlagPair> {
    match x {
        x => {
            value_dup_copy(*x)
        },
    }
}

pub fn pixel_replace_first(x0: Pixel, c: Color) -> Pixel {
    match (x0, c) {
        (Pixel::Pixel(r, g, b), c) => {
            Pixel::Pixel(c, g, b)
        },
    }
}

pub fn pixel_replace_first_borrow(x0: &Pixel, c: &Color) -> Pixel {
    match (*x0, *c) {
        (Pixel::Pixel(r, g, b), c) => {
            Pixel::Pixel(c, g, b)
        },
    }
}

pub fn use_wrap_dup_generic<A>(x: CopyWrap<A>) -> Prod<CopyWrap<A>, CopyWrap<A>> where A: Clone {
    match x {
        x => {
            wrap_dup(x.clone())
        },
    }
}

pub fn use_wrap_dup_generic_borrow<A>(x: &CopyWrap<A>) -> Prod<CopyWrap<A>, CopyWrap<A>> {
    match x {
        x => {
            wrap_dup_borrow(x)
        },
    }
}

pub fn nested_wrap_unwrap_flag(x0: NestedCopyWrap<FlagPair>) -> FlagPair {
    match x0 {
        NestedCopyWrap::NestedCopyWrap(CopyWrap::CopyWrap(x)) => {
            x
        },
    }
}

pub fn nested_wrap_unwrap_flag_borrow(x0: &NestedCopyWrap<FlagPair>) -> FlagPair {
    match x0 {
        NestedCopyWrap::NestedCopyWrap(CopyWrap::CopyWrap(x)) => {
            *x
        },
    }
}

