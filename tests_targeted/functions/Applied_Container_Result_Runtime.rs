// Copy into export1/tests/applied_container_result.rs after generating the theory.
// The HOL lemmas prove that each exported predicate equals Boolean negation.
// Exhaust both input values through the nested-application path and its direct
// control; generated function equality evaluates the callbacks extensionally.
use isabelle_exported::AppliedContainerResult::{
    callback_direct_matches, callback_matches,
};

#[test]
fn nested_applications_preserve_callback_results() {
    assert!(callback_matches(false));
    assert!(!callback_matches(true));
}

#[test]
fn direct_call_preserves_the_same_results() {
    assert!(callback_direct_matches(false));
    assert!(!callback_direct_matches(true));
}
