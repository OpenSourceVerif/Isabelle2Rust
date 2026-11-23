// After make gen DIR=tests_targeted/classes Name=Superclass_Closure_Bounds_Test:
// rustc +1.94.0 --edition=2024 --test -Awarnings \
//   tests_targeted/classes/Superclass_Closure_Bounds_Runtime.rs -o /tmp/closure-bounds
// /tmp/closure-bounds
//
// These independent Rust inhabitants implement only one sibling class each.
// Their calls check the executable HOL equations; missing superclass methods
// are never invoked. The third export must retain its real equality method.
#[path = "stage1/Superclass_Closure_Bounds_Test/export1/src/ClosureBounds.rs"]
mod missing;
#[path = "stage1/Superclass_Closure_Bounds_Test/export2/src/ClosureComplete.rs"]
mod complete;
#[path = "stage1/Superclass_Closure_Bounds_Test/export3/src/ClosureOperational.rs"]
mod operational;

#[derive(Clone)]
struct LeftOnly(bool);
#[derive(Clone)]
struct RightOnly(bool);

macro_rules! inhabitants {
    ($code:ident) => {
        impl $code::ClosureBase for LeftOnly {
            fn closure_base_op(x: Self) -> bool { x.0 }
        }
        impl $code::ClosureBase for RightOnly {
            fn closure_base_op(x: Self) -> bool { x.0 }
        }
        impl $code::ClosureParent for LeftOnly {
            fn closure_parent_op(x: Self) -> bool { x.0 }
        }
        impl $code::ClosureParent for RightOnly {
            fn closure_parent_op(x: Self) -> bool { x.0 }
        }
        impl $code::ClosureLeft for LeftOnly {
            fn closure_left_op(x: Self) -> bool { x.0 }
        }
        impl $code::ClosureRight for RightOnly {
            fn closure_right_op(x: Self) -> bool { !x.0 }
        }
    };
}
inhabitants!(missing);
inhabitants!(complete);
inhabitants!(operational);

impl operational::Equal for LeftOnly {
    fn equal(x: Self, y: Self) -> bool { x.0 == y.0 }
}
impl operational::Equal for RightOnly {
    fn equal(x: Self, y: Self) -> bool { x.0 == y.0 }
}

#[test]
fn independent_siblings_satisfy_both_missing_superclasses() {
    use missing::{ClosureBox::ClosureBox, *};
    for b in [false, true] {
        assert_eq!(closure_left_result(ClosureBox(LeftOnly(b))), b);
        assert_eq!(closure_right_result(ClosureBox(RightOnly(b))), !b);
    }
}

#[test]
fn reachable_base_keeps_its_executable_method() {
    use complete::{ClosureBox::ClosureBox, *};
    for b in [false, true] {
        assert_eq!(closure_left_result(ClosureBox(LeftOnly(b))), b);
        assert_eq!(closure_right_result(ClosureBox(RightOnly(b))), !b);
        assert_eq!(closure_base_result(ClosureBox(LeftOnly(b))), b);
        assert_eq!(closure_base_result(ClosureBox(RightOnly(b))), b);
    }
}

#[test]
fn missing_parent_retains_operational_equality() {
    use operational::{ClosurePair::ClosurePair, *};
    for x in [false, true] {
        for y in [false, true] {
            assert_eq!(closure_pair_left(ClosurePair(LeftOnly(x), LeftOnly(y))), x);
            assert_eq!(closure_pair_right(ClosurePair(RightOnly(x), RightOnly(y))), !y);
            assert_eq!(closure_pair_base(ClosurePair(LeftOnly(x), LeftOnly(y))), x == y);
        }
    }
}
