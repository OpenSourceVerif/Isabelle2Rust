// Runtime companion to Abort_Protocol_Test.thy. After make gen, copy this
// file to export1/tests/abort_protocol.rs and run cargo test --test abort_protocol.
// Catch actual generated panics: compiling alone cannot establish message
// preservation, panic timing, or non-execution of a supplied fallback.
use isabelle_exported::AbortProtocol as code;
use std::cell::Cell;
use std::panic::{catch_unwind, AssertUnwindSafe};
use std::rc::Rc;

fn literal(bytes: &[u8]) -> code::Literal {
    bytes.iter().rev().fold(code::Literal::ZeroLiteral, |tail, &b| {
        assert!(b < 128);
        code::Literal::Literal(
            b & 1 != 0, b & 2 != 0, b & 4 != 0, b & 8 != 0,
            b & 16 != 0, b & 32 != 0, b & 64 != 0, Box::new(tail),
        )
    })
}

fn panic_message<T>(f: impl FnOnce() -> T) -> String {
    match catch_unwind(AssertUnwindSafe(f)) {
        Ok(_) => panic!("generated abort unexpectedly returned"),
        Err(payload) => payload.downcast::<String>()
            .map(|s| *s)
            .unwrap_or_else(|_| panic!("generated abort lost its string message")),
    }
}

#[test]
fn messages_preserve_static_and_all_dynamic_ascii() {
    assert_eq!(panic_message(|| code::abort_bool(code::abort_message(), false)), "abort test");
    let bytes: Vec<u8> = (0..128).collect();
    assert_eq!(panic_message(|| code::abort_bool(literal(&bytes), false)),
        String::from_utf8(bytes).unwrap());
    assert_eq!(panic_message(|| code::abort_bool(literal(b""), false)), "");
}

#[test]
fn untaken_branch_returns_without_panicking() {
    assert!(code::abort_bool(code::abort_message(), true));
}

#[test]
fn partial_abort_is_lazy_and_never_calls_the_fallback() {
    let partial = match code::abort_partial(literal(b"partial")) {
        code::Option::Some(f) => f,
        _ => panic!("partial abort lost its function"),
    };
    let called = Rc::new(Cell::new(false));
    let observed = called.clone();
    let fallback = Rc::new(move |_: code::Unit| {
        observed.set(true);
        false
    });
    assert_eq!(panic_message(|| partial(fallback)), "partial");
    assert!(!called.get());
}

#[test]
fn unapplied_abort_preserves_both_protocol_arguments() {
    let abort = match code::abort_unapplied() {
        code::Option::Some(f) => f,
        _ => panic!("unapplied abort lost its function"),
    };
    let fallback = Rc::new(|_: code::Unit| panic!("fallback was evaluated"));
    assert_eq!(panic_message(|| abort(literal(b"unapplied"), fallback)), "unapplied");
}

#[test]
fn function_results_panic_before_returning_a_function() {
    assert_eq!(panic_message(|| code::abort_result_function(literal(b"function"))), "function");
    assert_eq!(panic_message(|| code::abort_apply_function(literal(b"applied"), true)), "applied");
    assert_eq!(panic_message(|| code::abort_operand(literal(b"operand"), true)), "operand");
}
