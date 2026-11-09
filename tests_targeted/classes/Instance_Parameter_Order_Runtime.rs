// Copy into export1/tests/instance_parameter_order.rs after generating the theory.
// The executable reader must dispatch through the dictionary of the second
// field after its type variables are aligned with the impl representative.
// Vec<bool> deliberately has no Marked implementation: compiling these calls
// also checks that alignment does not impose the second field's bound on it.
use isabelle_exported::InstanceParameterOrder::*;

#[test]
fn concrete_unit_bool_calls() {
    for value in [false, true] {
        assert_eq!(concrete_probe(Unit::Unity, value), value);
        assert_eq!(concrete_right_mark(Unit::Unity, value), value);
    }
}

#[test]
fn generic_reader_uses_only_the_right_dictionary() {
    for len in 0..=3 {
        for bits in 0..(1 << len) {
            let left: Vec<bool> = (0..len).map(|i| bits & (1 << i) != 0).collect();
            for value in [false, true] {
                let pair = PairBox::PairBox(left.clone(), value);
                assert_eq!(right_probe(pair.clone()), value);
                assert_eq!(<PairBox<Vec<bool>, bool> as BoxProbe>::box_read(pair.clone()), value);
                assert_eq!(right_mark(pair), value);
            }
        }
    }
}
