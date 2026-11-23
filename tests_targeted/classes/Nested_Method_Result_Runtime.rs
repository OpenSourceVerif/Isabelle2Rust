// Copy into export1/tests/nested_method_result.rs after generating the theory.
// Exercise the trait boundary itself: the outer callback returns Self as a
// function value, and both layers remain reusable after capturing the input.
// Exhaustive small boolean domains check results as well as the Rust signatures.
use isabelle_exported::NestedMethodResult::*;
use std::rc::Rc;

#[test]
fn absent_function_codec() {
    assert!(matches!(function_codec(), Option::None));
}

#[test]
fn unit_codec_callbacks() {
    let (encode, decode) = match unit_codec() {
        Option::Some(pair) => pair,
        Option::None => panic!("unit codec must be present"),
    };
    assert!(matches!(encode(Unit::Unity), List::Nil));
    // All 15 boolean lists with length at most three decode to unit.
    for len in 0..=3 {
        for bits in 0..(1 << len) {
            let mut xs = List::Nil;
            for i in 0..len {
                xs = List::Cons(bits & (1 << i) != 0, Box::new(xs));
            }
            assert!(matches!(decode(xs), Unit::Unity));
        }
    }
}

#[test]
fn constructed_callback_returns_reusable_function() {
    type BoolFn = Rc<dyn Fn(bool) -> bool>;
    // All four unary boolean functions; both selectors; repeated inner calls.
    for table in 0..4u8 {
        let f: BoolFn = Rc::new(move |x| table & (1 << u8::from(x)) != 0);
        assert!(matches!(
            <BoolFn as NestedFactory>::make_callback(false, f.clone()),
            Option::None
        ));
        let callback = match <BoolFn as NestedFactory>::make_callback(true, f) {
            Option::Some(callback) => callback,
            Option::None => panic!("enabled factory must return a callback"),
        };
        for selector in [false, true] {
            let returned = callback(selector);
            for x in [false, true] {
                let expected = table & (1 << u8::from(x)) != 0;
                assert_eq!(returned(x), expected);
                assert_eq!(returned(x), expected);
            }
        }
    }
}
