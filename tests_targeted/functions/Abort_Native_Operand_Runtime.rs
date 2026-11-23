//! Native operator operands must retain the HOL result type of Code.abort.
//! Validate generated panics and safe return values, including dynamic ASCII
//! messages, callback creation, and a supplied fallback with an observable flag.
use isabelle_exported::AbortNativeOperand as code;
use num_bigint::BigInt;
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

fn messages() -> Vec<Vec<u8>> {
    vec![vec![], b"native operand".to_vec(), (0..128).collect()]
}

fn values() -> Vec<BigInt> {
    let large = BigInt::from(1) << 130usize;
    vec![-large.clone(), BigInt::from(0), large + BigInt::from(7)]
}

fn panic_message<T>(f: impl FnOnce() -> T) -> String {
    match catch_unwind(AssertUnwindSafe(f)) {
        Ok(_) => panic!("generated abort unexpectedly returned"),
        Err(payload) => payload.downcast::<String>()
            .map(|s| *s)
            .unwrap_or_else(|_| panic!("generated abort lost its dynamic message")),
    }
}

#[test]
fn native_operators_and_consumed_result_arrows_preserve_the_message() {
    for bytes in messages() {
        let expected = String::from_utf8(bytes.clone()).unwrap();
        assert_eq!(panic_message(|| code::abort_integer_negate(literal(&bytes))), expected);
        for value in values() {
            assert_eq!(panic_message(|| code::abort_integer_left(literal(&bytes), value.clone())), expected);
            assert_eq!(panic_message(|| code::abort_integer_right(literal(&bytes), value.clone())), expected);
            assert_eq!(panic_message(|| code::abort_integer_compare(literal(&bytes), value.clone())), expected);
            assert_eq!(panic_message(|| code::abort_integer_safe(true, literal(&bytes), value.clone())), expected);
            // The generated source contains a second abort as the later
            // argument. Its "argument evaluated" message must never replace this.
            assert_eq!(panic_message(|| code::abort_apply_integer(literal(&bytes), value.clone())), expected);
            assert_eq!(code::abort_integer_safe(false, literal(&bytes), value.clone()), value);
        }
    }
}

#[test]
fn callback_creation_remains_delayed() {
    for bytes in messages() {
        let expected = String::from_utf8(bytes.clone()).unwrap();
        let callback = match code::abort_integer_delayed(literal(&bytes)) {
            code::Option::Some(callback) => callback,
            _ => panic!("callback was not returned"),
        };
        for value in values() {
            assert_eq!(panic_message(|| callback(value)), expected);
        }
    }
}

#[test]
fn partial_abort_never_calls_its_fallback() {
    for bytes in messages() {
        let expected = String::from_utf8(bytes.clone()).unwrap();
        let abort = match code::abort_partial_integer(literal(&bytes)) {
            code::Option::Some(abort) => abort,
            _ => panic!("partial abort was not returned"),
        };
        let called = Rc::new(Cell::new(false));
        let observed = called.clone();
        let fallback = Rc::new(move |_: code::Unit| {
            observed.set(true);
            BigInt::from(99)
        });
        assert_eq!(panic_message(|| abort(fallback)), expected);
        assert!(!called.get());
    }
}
