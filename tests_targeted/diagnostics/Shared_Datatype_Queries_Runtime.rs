// Copy to export1/tests/shared_datatype_queries.rs after generating the theory.
// The empty branch requires the recursive-only marker. The productive branch
// acquires its witness through another datatype in the recursive group. Two differently
// instantiated WitnessSlot fields must together witness both outer parameters.
use isabelle_exported::SharedDatatypeQueries::*;
use std::marker::PhantomData;

#[test]
fn recursive_witnesses_preserve_values() {
    for bit in [false, true] {
        let once: GateLeft<Vec<bool>, bool> = gate_wrap(bit);
        let twice: GateLeft<Vec<bool>, bool> = gate_twice(bit);
        assert!(matches!(gate_read(once), Option::Some(value) if value == bit));
        assert!(matches!(gate_read(twice), Option::Some(value) if value == bit));
    }
}

#[test]
fn empty_recursive_branch_retains_the_phantom_field() {
    let empty: GateLeft<Vec<bool>, bool> = GateLeft::GateEnd(PhantomData);
    assert!(matches!(gate_read(empty), Option::None));
}

#[test]
fn distinct_applications_witness_both_parameters() {
    for len in 0..=5 {
        for bit in [false, true] {
            let first = vec![bit; len];
            let value: WitnessPair<Vec<bool>, bool> = witness_make(first.clone(), !bit);
            assert_eq!(witness_observe(value.clone()), (first, !bit));
            // No outer PhantomData field is permitted when both parameters
            // already have a nonrecursive witness through the two slot types.
            let WitnessPair::WitnessPair(_) = value;
        }
    }
}
