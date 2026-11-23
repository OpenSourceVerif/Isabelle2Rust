// Copy to export1/tests/shared_shape_substitution.rs after generating the theory.
// Ordinary export retains Itself<A> and its phantom argument. Check that both
// the single call and nested polymorphic calls accept and return
// witnesses for unrelated types with the standard, non-erased signatures.
use isabelle_exported::SharedExpectedBinding::*;
use std::marker::PhantomData;

fn witness<A>() -> Itself<A> {
    Itself::Type(PhantomData)
}

#[test]
fn single_call_control_preserves_its_witness() {
    assert!(matches!(witness_forward::<bool>(witness()), Itself::Type(_)));
    assert!(matches!(witness_forward::<Vec<bool>>(witness()), Itself::Type(_)));
    assert!(matches!(witness_forward::<(bool, bool)>(witness()), Itself::Type(_)));
}

#[test]
fn nested_call_preserves_its_witness() {
    assert!(matches!(witness_nested::<bool>(witness()), Itself::Type(_)));
    assert!(matches!(witness_nested::<Vec<bool>>(witness()), Itself::Type(_)));
    assert!(matches!(witness_nested::<(bool, bool)>(witness()), Itself::Type(_)));
}
