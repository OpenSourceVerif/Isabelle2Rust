// Runtime companion to Closure_Pattern_Test.thy. Copy to the generated
// export1/tests/closure_patterns.rs and run cargo test --test closure_patterns.
// Successful pattern cases must preserve results and reusable captures. Cases
// omitted by the HOL definition keep the backend's existing invocation-time
// panic convention, rather than failing while the closure value is constructed.
use isabelle_exported::ClosurePatterns as code;
use std::panic::{catch_unwind, AssertUnwindSafe};

fn some<T>(value: code::Option<T>) -> T {
    match value {
        code::Option::Some(x) => x,
        _ => panic!("generated function value missing"),
    }
}

fn wrapped(x: bool) -> code::ClosureWrapper {
    code::ClosureWrapper::Wrapped(code::ClosureCore::Seen(x), false)
}

fn missing() -> code::ClosureWrapper {
    code::ClosureWrapper::Wrapped(code::ClosureCore::Missing, false)
}

fn list(xs: &[bool]) -> code::List<bool> {
    xs.iter().rev().fold(code::List::Nil, |tail, &x| {
        code::List::Cons(x, Box::new(tail))
    })
}

#[test]
fn nested_refutable_pattern_and_capture_stay_callable() {
    let direct = some(code::refutable_closure());
    for flag in [false, true] {
        let captured = some(code::capture_closure(flag));
        for x in [false, true] {
            assert_eq!(direct(wrapped(x)), x);
            assert_eq!(captured(wrapped(x)), flag && x);
        }
        assert!(catch_unwind(AssertUnwindSafe(|| captured(missing()))).is_err());
    }
    assert!(catch_unwind(AssertUnwindSafe(|| direct(missing()))).is_err());
}

#[test]
fn nested_boxed_list_pattern_accepts_exactly_two_elements() {
    let f = some(code::nested_list_closure());
    for x in [false, true] {
        for y in [false, true] {
            assert_eq!(f(list(&[x, y])), x && y);
        }
    }
    for xs in [&[][..], &[true][..], &[true, false, true][..]] {
        assert!(catch_unwind(AssertUnwindSafe(|| f(list(xs)))).is_err());
    }
}

#[test]
fn irrefutable_parameters_preserve_their_results() {
    let f = some(code::tuple_closure());
    let single = some(code::single_closure());
    for x in [false, true] {
        assert_eq!(single(code::ClosureSingle::Sole(x)), x);
        for y in [false, true] {
            assert_eq!(f((x, y)), x && y);
        }
    }
}

#[test]
fn retained_case_preserves_the_function_valued_result() {
    let f = some(code::result_closure());
    for x in [false, true] {
        for y in [false, true] {
            assert_eq!(f(wrapped(x), y), x && y);
        }
    }
    assert!(catch_unwind(AssertUnwindSafe(|| f(missing(), true))).is_err());
}
