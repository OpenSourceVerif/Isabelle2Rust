#[derive(Clone, Copy)]
pub enum MutColor {
    MRed,
    MGreen,
    MBlue,
}

// borrow-optimized by shared parameters
pub fn color_next(x0: &MutColor) -> MutColor {
    match x0 {
        MutColor::MRed => {
            MutColor::MGreen
        },
        MutColor::MGreen => {
            MutColor::MBlue
        },
        MutColor::MBlue => {
            MutColor::MRed
        },
    }
}

// borrow-optimized by shared parameters
pub fn color_tint(x0: &bool, c: &MutColor) -> MutColor {
    match (*x0, *c) {
        (true, c) => {
            c
        },
        (false, c) => {
            color_next(&c)
        },
    }
}

// borrow-optimized by shared parameters
pub fn color_step(flag: &bool, c: &MutColor) -> MutColor {
    match (*flag, *c) {
        (flag, c) => {
            color_tint(&flag, &color_next(&c))
        },
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn color_adjacent_chain(c: &MutColor) -> MutColor {
    {
        let mut x = *c;
        x = color_next(&x);
        x = color_tint(&true, &x);
        x
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn color_call_rhs_chain(flag: &bool, c: &MutColor) -> MutColor {
    {
        let mut x = *c;
        x = color_step(flag, &x);
        x = color_step(&!flag.clone(), &x);
        x
    }
}

// borrow-optimized by shared parameters
// mut-optimized by in-place updates
pub fn color_interleaved_chain(seed: &bool, c: &MutColor) -> MutColor {
    {
        let mut x = *c;
        let flag = *seed;
        x = color_tint(&flag, &x);
        let flaga = !flag.clone();
        x = color_tint(&flaga.clone(), &color_next(&x));
        x
    }
}

// borrow-optimized by shared parameters
pub fn color_saved_value_blocks_chain(c: &MutColor) -> crate::Product_Type::Prod<MutColor, MutColor> {
    {
        let x = *c;
        let saved = x;
        let a = color_next(&x);
        crate::Product_Type::Prod::Pair(saved, a)
    }
}

