// Copy to export1/tests/exception_generics.rs after generating the theory.
// A code-aborting constant must remain a panic at the point of application.
// In particular, eta expansion must not evaluate it when constructing a
// function value, and the declaration-order repair must not affect safe arms.
use isabelle_exported::ExceptionGenerics::*;
use std::panic::{catch_unwind, AssertUnwindSafe};

fn expect_missing<T>(f: impl FnOnce() -> T) {
    let payload = match catch_unwind(AssertUnwindSafe(f)) {
        Ok(_) => panic!("code-aborting constant unexpectedly returned"),
        Err(payload) => payload,
    };
    let message = payload.downcast_ref::<String>().map(String::as_str)
        .or_else(|| payload.downcast_ref::<&str>().copied());
    assert_eq!(message, Some("Exception_Generic_Order_Test.missing_result"));
}

#[test]
fn saturated_calls_preserve_the_exception() {
    expect_missing(|| exception_concrete(List::<bool>::Nil));
    expect_missing(|| exception_generic(List::Cons(Unit::Unity, Box::new(List::Nil))));
    expect_missing(|| exception_safe(true));
}

#[test]
fn delayed_calls_raise_only_when_applied() {
    let delayed = exception_delayed(true);
    expect_missing(|| (*delayed)(List::<Unit>::Nil));
}

#[test]
fn safe_branches_return_their_original_values() {
    assert!(matches!(exception_safe(false), Option::Some(false)));
    let safe = exception_delayed(false);
    assert!(matches!((*safe)(List::<Unit>::Nil), Option::Some(true)));
}
