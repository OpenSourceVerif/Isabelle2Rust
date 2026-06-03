#![feature(box_patterns)]

#[path = "../Generic_Copy_Bound_Test.rs"]
mod Generic_Copy_Bound_Test;
#[path = "../Product_Type.rs"]
mod Product_Type;

use Generic_Copy_Bound_Test::{duplicate_value, duplicate_wrap, CopyWrap};

fn main() {
    let _ = duplicate_value(String::from("non-copy"));
    let _ = duplicate_wrap(CopyWrap::CopyWrap(String::from("non-copy")));
}
