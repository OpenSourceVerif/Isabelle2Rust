// Copy to export1/tests/shared_shape_substitution.rs after generating the theory.
// Ordinary export retains Itself<A> and its phantom argument. Check that both
// the direct identity and the generated polymorphic call accept and return
// witnesses for unrelated types with the standard, non-erased signatures.
use isabelle_exported::SharedShapeSubstitution::*;
use std::marker::PhantomData;

fn witness<A>() -> Itself<A> {
    Itself::Type(PhantomData)
}

#[test]
fn identity_control_preserves_its_witness() {
    assert!(matches!(witness_identity::<bool>(witness()), Itself::Type(_)));
    assert!(matches!(witness_identity::<Vec<bool>>(witness()), Itself::Type(_)));
    assert!(matches!(witness_identity::<(bool, bool)>(witness()), Itself::Type(_)));
}

#[test]
fn ordinary_wrapper_preserves_its_witness() {
    assert!(matches!(witness_forward::<bool>(witness()), Itself::Type(_)));
    assert!(matches!(witness_forward::<Vec<bool>>(witness()), Itself::Type(_)));
    assert!(matches!(witness_forward::<(bool, bool)>(witness()), Itself::Type(_)));
}
