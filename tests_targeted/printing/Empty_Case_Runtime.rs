//! Empty Thingol cases follow the backend's existing undefined-code panic
//! convention. Check the panic identity as well as delayed and short-circuit
//! evaluation; a parser-only check would not catch eager callback evaluation.
use isabelle_exported::EmptyCase::*;
use std::panic::{catch_unwind, AssertUnwindSafe};

fn assert_empty_case_panic<T>(f: impl FnOnce() -> T) {
    let payload = match catch_unwind(AssertUnwindSafe(f)) {
        Ok(_) => panic!("undefined case unexpectedly returned"),
        Err(payload) => payload,
    };
    let message = payload.downcast_ref::<&str>().copied()
        .or_else(|| payload.downcast_ref::<String>().map(String::as_str));
    assert_eq!(message, Some("empty case"));
}

fn inputs() -> [Option<bool>; 3] {
    [Option::None, Option::Some(false), Option::Some(true)]
}

#[test]
fn empty_cases_diverge_in_scalar_generic_and_boxed_positions() {
    for input in inputs() {
        assert_empty_case_panic(|| empty_case_value(input.clone()));
        assert_empty_case_panic(|| empty_case_generic::<(), bool>(input.clone()));
        assert_empty_case_panic(|| empty_case_field(input.clone()));
        assert_empty_case_panic(|| empty_case_integer(input.clone()));
    }
}

#[test]
fn safe_branches_and_short_circuit_operands_remain_executable() {
    for input in inputs() {
        assert!(safe_empty_case(false, input.clone()));
        assert_empty_case_panic(|| safe_empty_case(true, input.clone()));
        assert!(!empty_case_operand(false, input.clone()));
        assert_empty_case_panic(|| empty_case_operand(true, input.clone()));
    }
}

#[test]
fn stored_callbacks_fail_only_when_the_undefined_callback_is_called() {
    for enabled in [false, true] {
        // Both callback values must be constructible before any application.
        let EmptyCallback::EmptyCallback(callback) = empty_case_callback(enabled);
        for input in inputs() {
            if enabled {
                assert_empty_case_panic(|| callback(input.clone()));
            } else {
                assert!(!callback(input.clone()));
            }
        }
    }
}

#[test]
fn partial_empty_function_values_keep_their_missing_argument() {
    for scrutinee in inputs() {
        for bound in [false, true] {
            // Ordinary partial application constructs a closure first. The
            // empty function case is reached on the completed application.
            let EmptyCallback::EmptyCallback(callback) =
                partial_empty_case(scrutinee.clone(), bound);
            for argument in inputs() {
                assert_empty_case_panic(|| callback(argument.clone()));
            }
        }
    }
}
