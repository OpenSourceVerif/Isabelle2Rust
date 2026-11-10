// Copy to export1/tests/shared_shape_erasure.rs after generating the theory.
// Identity and both Boolean equations retain the witness value after result
// layout validation. Unrelated generic arguments check fresh serializer state.
use isabelle_exported::SharedShapeErasure::*;

#[test]
fn erased_identity_preserves_its_witness() {
    assert_eq!(witness_identity::<bool>(()), ());
    assert_eq!(witness_identity::<Vec<bool>>(()), ());
    assert_eq!(witness_identity::<(bool, bool)>(()), ());
}

#[test]
fn both_equations_preserve_their_witness() {
    for selector in [false, true] {
        assert_eq!(witness_branches::<bool>(selector, ()), ());
        assert_eq!(witness_branches::<Vec<bool>>(selector, ()), ());
        assert_eq!(witness_branches::<(bool, bool)>(selector, ()), ());
    }
}
