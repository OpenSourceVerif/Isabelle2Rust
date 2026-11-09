// Runtime companion: copy into export1/tests/computed_callee_ownership.rs.
// Every token is Clone but not Copy. Exercise both selector branches for each
// generic call path and compare against the equality theorem in the HOL test.
use isabelle_exported::ComputedCalleeOwnership as code;

fn token(n: u8) -> code::CalleeToken {
    code::CalleeToken::Token(n & 1 != 0, n & 2 != 0)
}

fn check(f: fn(code::CalleeToken, code::CalleeToken, code::CalleeToken) -> bool) {
    for a in 0..4 {
        for b in 0..4 {
            for c in 0..4 {
                assert_eq!(f(token(a), token(b), token(c)), a == c,
                           "tokens a={a}, b={b}, c={c}");
            }
        }
    }
}

#[test]
fn trait_condition_preserves_later_captures() {
    check(code::callee_trait_reuse);
}

#[test]
fn ordinary_condition_preserves_later_captures() {
    check(code::callee_function_reuse);
}

#[test]
fn concrete_wrapper_agrees_with_hol() {
    check(code::callee_concrete);
}
