// Runtime companion to Registered_Result_Test.thy. Copy into the generated
// export1/tests/registered_result.rs and run cargo test --test registered_result.
// Exercise the actual emitted calls: compilation cannot detect argument swaps,
// premature execution during eta expansion, or repeated callback evaluation.
use isabelle_exported::RegisteredResult as code;
use std::cell::Cell;
use std::rc::Rc;

#[test]
fn fully_applied_returned_function_preserves_argument_order() {
    let f = Rc::new(|x: bool, y: bool| x && !y);
    for x in [false, true] {
        for y in [false, true] {
            assert_eq!(code::syntax_full(f.clone(), x, y), x && !y);
        }
    }
}

#[test]
fn partial_application_delays_and_calls_once() {
    let calls = Rc::new(Cell::new(0));
    let observed = calls.clone();
    let f = Rc::new(move |x: bool, y: bool| {
        observed.set(observed.get() + 1);
        x && !y
    });
    let partial = match code::syntax_partial(f) {
        code::Option::Some(f) => f,
        _ => panic!("partial application lost its function"),
    };
    assert_eq!(calls.get(), 0);
    assert!(partial(false));
    assert_eq!(calls.get(), 1);
    assert!(!partial(true));
    assert_eq!(calls.get(), 2);
}

#[test]
fn zero_placeholder_template_returns_callable_functions() {
    let whole = match code::syntax_native_whole() {
        code::Option::Some(f) => f,
        _ => panic!("native function value lost"),
    };
    let partial = match code::syntax_native_partial() {
        code::Option::Some(f) => f,
        _ => panic!("native partial application lost"),
    };
    for x in [false, true] {
        assert_eq!(partial(x), x);
        for y in [false, true] {
            assert_eq!(whole(x, y), x && y);
        }
    }
}

#[test]
fn plain_path_works_as_an_item_call_and_a_function_value() {
    let value = match code::syntax_plain_value() {
        code::Option::Some(f) => f,
        _ => panic!("plain function path lost"),
    };
    for x in [false, true] {
        assert_eq!(code::syntax_plain_call(x), !x);
        assert_eq!(value(x), !x);
    }
}
